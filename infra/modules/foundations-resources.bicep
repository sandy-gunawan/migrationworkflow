param location string
param appServiceLocation string
param operatorPrincipalId string
param foundryProjectPrincipalId string
param apiApplicationId string

@secure()
param fabricAdministrator string

var suffix = '48254cc6'
var tenantId = subscription().tenantId
var tags = {
  demo_id: suffix
  workload: 'mining-migration'
  data_classification: 'synthetic-only'
  managed_by: 'kpp-demo'
}

resource plan 'Microsoft.Web/serverfarms@2024-11-01' = {
  name: 'kppdemo-linux-${suffix}'
  location: appServiceLocation
  kind: 'linux'
  tags: tags
  sku: {
    name: 'B1'
    tier: 'Basic'
    capacity: 1
  }
  properties: {
    reserved: true
  }
}

resource backing 'Microsoft.Web/sites@2024-11-01' = {
  name: 'kppdemo-data-${suffix}'
  location: appServiceLocation
  kind: 'app,linux'
  tags: union(tags, { 'azd-service-name': 'backing' })
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.13'
      appCommandLine: 'python -m uvicorn backing_service.app:create_app --factory --host 0.0.0.0 --port 8000'
      alwaysOn: true
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      healthCheckPath: '/health'
    }
  }
}

resource maf 'Microsoft.Web/sites@2024-11-01' = {
  name: 'kppdemo-maf-${suffix}'
  location: appServiceLocation
  kind: 'app,linux'
  tags: union(tags, { 'azd-service-name': 'maf' })
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.13'
      appCommandLine: 'cd /home/site/wwwroot && python -m uvicorn maf_service.app:create_app --factory --host 0.0.0.0 --port 8000'
      alwaysOn: true
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      healthCheckPath: '/health'
    }
  }
}

resource search 'Microsoft.Search/searchServices@2025-05-01' = {
  name: 'kppsearch${suffix}'
  location: location
  tags: tags
  sku: {
    name: 'basic'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'Default'
    publicNetworkAccess: 'enabled'
    disableLocalAuth: true
    semanticSearch: 'free'
  }
}

resource fabric 'Microsoft.Fabric/capacities@2026-09-01-preview' = {
  name: 'kppfabric${suffix}'
  location: location
  tags: tags
  sku: {
    name: 'F2'
    tier: 'Fabric'
  }
  properties: {
    administration: {
      members: [
        fabricAdministrator
      ]
    }
    overage: {
      state: 'Disabled'
      thresholdCapacityUnitHours: 0
    }
  }
}

resource backingSettings 'Microsoft.Web/sites/config@2024-11-01' = {
  parent: backing
  name: 'appsettings'
  properties: {
    SCM_DO_BUILD_DURING_DEPLOYMENT: 'false'
    ENABLE_ORYX_BUILD: 'false'
    PYTHONPATH: '/home/site/wwwroot/.python_packages/lib/site-packages'
    DEMO_ID: suffix
    DEMO_TENANT_ID: tenantId
    DEMO_API_AUDIENCE: apiApplicationId
    DEMO_API_RESOURCE: 'api://${apiApplicationId}'
    DEMO_ALLOWED_CALLER_IDS: join([
      operatorPrincipalId
      maf.identity.principalId
      foundryProjectPrincipalId
      backing.identity.principalId
    ], ',')
    DEMO_AUTH_MODE: 'entra'
    DEMO_SEARCH_ENDPOINT: 'https://${search.name}.search.windows.net'
  }
}

resource mafSettings 'Microsoft.Web/sites/config@2024-11-01' = {
  parent: maf
  name: 'appsettings'
  properties: {
    SCM_DO_BUILD_DURING_DEPLOYMENT: 'false'
    ENABLE_ORYX_BUILD: 'false'
    PYTHONPATH: '/home/site/wwwroot/.python_packages/lib/site-packages'
    DEMO_ID: suffix
    DEMO_TENANT_ID: tenantId
    DEMO_API_AUDIENCE: apiApplicationId
    DEMO_API_RESOURCE: 'api://${apiApplicationId}'
    DEMO_ALLOWED_CALLER_IDS: operatorPrincipalId
    DEMO_AUTH_MODE: 'entra'
    DEMO_BACKING_URL: 'https://${backing.properties.defaultHostName}'
    DEMO_FOUNDRY_ENDPOINT: 'https://kppfoundry48254cc6.services.ai.azure.com/api/projects/kpp-mining-demo'
    DEMO_FOUNDRY_AGENT_READINESS: 'kppdemo-isolated-readiness-48254cc6'
  }
}

var searchReaderRole = '1407120a-92aa-4202-b7e9-c0e197c71c8f'
var searchDataContributorRole = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
var searchServiceContributorRole = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
resource readerAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for index in range(0, 2): {
  name: guid(search.id, 'runtime-reader-${index}', searchReaderRole)
  scope: search
  properties: {
    principalId: index == 0 ? backing.identity.principalId : foundryProjectPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchReaderRole)
  }
}]

resource setupAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for roleId in [
  searchDataContributorRole
  searchServiceContributorRole
]: {
  name: guid(search.id, operatorPrincipalId, roleId)
  scope: search
  properties: {
    principalId: operatorPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleId)
  }
}]

output backingUrl string = 'https://${backing.properties.defaultHostName}'
output mafUrl string = 'https://${maf.properties.defaultHostName}'
output searchServiceId string = search.id
output searchEndpoint string = 'https://${search.name}.search.windows.net'
output fabricCapacityId string = fabric.id
output backingPrincipalId string = backing.identity.principalId
output mafPrincipalId string = maf.identity.principalId
