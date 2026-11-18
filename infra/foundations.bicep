targetScope = 'subscription'

param location string = 'southeastasia'
param appServiceLocation string = 'eastasia'
param resourceGroupName string = 'demo_kpp'
param operatorPrincipalId string
param foundryProjectPrincipalId string
param apiApplicationId string

@secure()
param fabricAdministrator string

resource demoGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: {
    demo_id: '48254cc6'
    workload: 'mining-migration'
    data_classification: 'synthetic-only'
  }
}

module resources 'modules/foundations-resources.bicep' = {
  name: 'kppdemo-foundation-resources'
  scope: demoGroup
  params: {
    location: location
    appServiceLocation: appServiceLocation
    operatorPrincipalId: operatorPrincipalId
    foundryProjectPrincipalId: foundryProjectPrincipalId
    apiApplicationId: apiApplicationId
    fabricAdministrator: fabricAdministrator
  }
}

module foundryAccess 'modules/foundry-runtime-access.bicep' = {
  name: 'kppdemo-runtime-project-access'
  scope: resourceGroup('foundry')
  params: {
    principalId: resources.outputs.mafPrincipalId
  }
}

output backingUrl string = resources.outputs.backingUrl
output mafUrl string = resources.outputs.mafUrl
output searchServiceId string = resources.outputs.searchServiceId
output searchEndpoint string = resources.outputs.searchEndpoint
output fabricCapacityId string = resources.outputs.fabricCapacityId
output backingPrincipalId string = resources.outputs.backingPrincipalId
output mafPrincipalId string = resources.outputs.mafPrincipalId
