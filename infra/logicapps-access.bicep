targetScope = 'resourceGroup'

param logicPrincipalId string
var name = 'kppdemo-mining-48254cc6'
var readerRole = 'acdd72a7-3385-48ef-bd42-f606fba81ae7'
var verifierPrincipalId = '0b8a21ad-1ce0-4eb4-ab64-dadc5fe13217'

resource workflow 'Microsoft.Logic/workflows@2019-05-01' existing = {
  name: name
}

resource historyReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(workflow.id, verifierPrincipalId, readerRole)
  scope: workflow
  properties: {
    principalId: verifierPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', readerRole)
  }
}

module foundryAccess 'modules/foundry-runtime-access.bicep' = {
  name: 'kppdemo-logic-foundry-access-48254cc6'
  scope: resourceGroup('foundry')
  params: {
    principalId: logicPrincipalId
    assignmentNameSeed: name
  }
}
