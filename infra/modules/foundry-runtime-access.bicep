param principalId string
param assignmentNameSeed string = 'kppdemo-maf-48254cc6'

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: 'kppfoundry48254cc6'
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = {
  parent: account
  name: 'kpp-mining-demo'
}

resource runtimeAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, assignmentNameSeed, '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  scope: project
  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  }
}
