targetScope = 'resourceGroup'

param location string = 'southeastasia'
@allowed(['Disabled', 'Enabled'])
param state string = 'Disabled'
var name = 'kppdemo-mining-48254cc6'
var definition = loadJsonContent('../targets/logicapps/workflow.json')

module workflow 'br/public:avm/res/logic/workflow:0.6.0' = {
  name: 'kppdemo-logic-workflow-48254cc6'
  params: {
    name: name
    location: location
    state: state
    enableTelemetry: false
    managedIdentities: {
      systemAssigned: true
    }
    tags: {
      demo_id: '48254cc6'
      workload: 'mining-migration'
      data_classification: 'synthetic-only'
      orchestrator: 'native-logic-apps'
    }
    workflowTriggers: definition.triggers
    workflowActions: definition.actions
    workflowOutputs: definition.outputs
    workflowParameters: {}
    triggersAccessControlConfiguration: {
      #disable-next-line BCP037 // Supported by the service; the 2019 schema predates SAS-disable support.
      sasAuthenticationPolicy: {
        state: 'Disabled'
      }
      openAuthenticationPolicies: {
        policies: {
          demoSetupManagedIdentity: {
            type: 'AAD'
            claims: [
              { name: 'iss', value: 'https://sts.windows.net/020201e2-0ae9-446c-8981-55a2bdecc00d/' }
              { name: 'aud', value: environment().resourceManager }
              { name: 'oid', value: '0b8a21ad-1ce0-4eb4-ab64-dadc5fe13217' }
            ]
          }
        }
      }
    }
  }
}

output workflowId string = workflow.outputs.resourceId
output principalId string = workflow.outputs.systemAssignedMIPrincipalId!
output workflowName string = workflow.outputs.name
