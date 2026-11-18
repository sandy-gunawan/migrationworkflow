targetScope = 'resourceGroup'

@description('Administrator for this new demo-only capacity; do not emit in outputs.')
@secure()
param fabricAdministrator string

resource capacity 'Microsoft.Fabric/capacities@2026-09-01-preview' = {
  name: 'kppfabricus48254cc6'
  location: 'eastus2'
  tags: {
    demo_id: '48254cc6'
    workload: 'mining-migration'
    data_classification: 'synthetic-only'
    managed_by: 'kpp-demo'
    purpose: 'native-fabric-us-region-test'
  }
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

output capacityId string = capacity.id
