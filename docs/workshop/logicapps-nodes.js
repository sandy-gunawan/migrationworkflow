"use strict";

window.logicWorkshop = {
  "nodes": [
    {
      "id": "kpp_mining_start",
      "title": "kpp mining start",
      "type": "Request",
      "group": "Alur contoh TRK001",
      "url": "<URL_TRIGGER_OAUTH>",
      "url_note": "URL yang dipakai UI demo.",
      "method": "POST",
      "parameters": [
        {
          "name": "api-version (URL)",
          "value": "2016-06-01; versi API trigger"
        },
        {
          "name": "question",
          "value": "string; wajib; 1-4000 karakter"
        },
        {
          "name": "run_id",
          "value": "string; UUID; opsional"
        },
        {
          "name": "Field tambahan",
          "value": "Ditolak"
        },
        {
          "name": "Autentikasi",
          "value": "Entra ID; SAS Disabled"
        }
      ],
      "input": {
        "question": "Show work orders for equipment TRK001."
      },
      "output": {
        "question": "Show work orders for equipment TRK001."
      },
      "raw": {
        "type": "Request",
        "kind": "Http",
        "inputs": {
          "method": "POST",
          "schema": {
            "additionalProperties": false,
            "properties": {
              "question": {
                "maxLength": 4000,
                "minLength": 1,
                "title": "Question",
                "type": "string"
              },
              "run_id": {
                "format": "uuid",
                "title": "Run Id",
                "type": "string"
              }
            },
            "required": [
              "question"
            ],
            "title": "DemoRequest",
            "type": "object"
          }
        },
        "runtimeConfiguration": {
          "secureData": {
            "properties": [
              "inputs"
            ]
          }
        }
      },
      "why": "UI/backend perlu satu pintu masuk HTTP untuk memulai proses.",
      "scenario": {
        "number": 1,
        "input": {
          "question": "Show work orders for equipment TRK001.",
          "run_id": "<ID_SANDBOX>"
        },
        "output": {
          "question": "Show work orders for equipment TRK001.",
          "run_id": "<ID_SANDBOX>"
        },
        "input_kind": "json",
        "output_kind": "json",
        "input_label": "Nilai masuk (contoh)",
        "output_label": "Output (contoh)"
      },
      "purpose": "Menerima pertanyaan dari UI/backend untuk memulai workflow."
    },
    {
      "id": "Validate_request",
      "title": "Validate request",
      "type": "ParseJson",
      "group": "Alur contoh TRK001",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Content",
          "value": "@triggerBody()"
        },
        {
          "name": "question",
          "value": "string; wajib; 1-4000 karakter"
        },
        {
          "name": "run_id",
          "value": "string; UUID; opsional"
        },
        {
          "name": "Field tambahan",
          "value": "Ditolak"
        }
      ],
      "input": "@triggerBody()",
      "output": {
        "question": "Show work orders for equipment TRK001."
      },
      "raw": {
        "type": "ParseJson",
        "runAfter": {},
        "inputs": {
          "content": "@triggerBody()",
          "schema": {
            "additionalProperties": false,
            "properties": {
              "question": {
                "maxLength": 4000,
                "minLength": 1,
                "title": "Question",
                "type": "string"
              },
              "run_id": {
                "format": "uuid",
                "title": "Run Id",
                "type": "string"
              }
            },
            "required": [
              "question"
            ],
            "title": "DemoRequest",
            "type": "object"
          }
        }
      },
      "why": "Node berikutnya perlu data dengan bentuk yang benar, bukan teks yang belum diperiksa.",
      "scenario": {
        "number": 2,
        "input": {
          "question": "Show work orders for equipment TRK001.",
          "run_id": "<ID_SANDBOX>"
        },
        "output": {
          "question": "Show work orders for equipment TRK001.",
          "run_id": "<ID_SANDBOX>"
        },
        "input_kind": "json",
        "output_kind": "json",
        "input_label": "Nilai masuk (contoh)",
        "output_label": "Output (contoh)"
      },
      "purpose": "Memeriksa bentuk input sebelum memanggil agent."
    },
    {
      "id": "capture_question",
      "title": "capture question",
      "type": "Compose",
      "group": "Alur contoh TRK001",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "question",
          "value": "@triggerBody()?['question']"
        },
        {
          "name": "run_id",
          "value": "@coalesce(triggerBody()?['run_id'],guid())"
        }
      ],
      "input": "Body dari trigger.",
      "output": {
        "question": "Show work orders for equipment TRK001.",
        "run_id": "<ID_SANDBOX>"
      },
      "raw": {
        "type": "Compose",
        "runAfter": {
          "Validate_request": [
            "Succeeded"
          ]
        },
        "inputs": {
          "question": "@triggerBody()?['question']",
          "run_id": "@coalesce(triggerBody()?['run_id'],guid())"
        }
      },
      "why": "Semua langkah perlu question dan run_id yang sama agar hasil dan log bisa dicocokkan.",
      "scenario": {
        "number": 3,
        "input": {
          "question": "Show work orders for equipment TRK001.",
          "run_id": "<ID_SANDBOX>"
        },
        "output": {
          "question": "Show work orders for equipment TRK001.",
          "run_id": "<ID_SANDBOX>"
        },
        "input_kind": "json",
        "output_kind": "json",
        "input_label": "Nilai masuk (contoh)",
        "output_label": "Output (contoh)"
      },
      "purpose": "Menyimpan question dan menyiapkan run_id untuk node berikutnya."
    },
    {
      "id": "Initialize_result",
      "title": "Initialize result",
      "type": "InitializeVariable",
      "group": "Alur contoh TRK001",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "NativeResponses",
          "value": "string; nilai awal kosong"
        },
        {
          "name": "Result",
          "value": "object; nilai awal status failed"
        }
      ],
      "input": "run_id dari capture_question.",
      "output": {
        "NativeResponses": "",
        "Result": {
          "run_id": "<ID_SANDBOX>",
          "route": "unsupported",
          "status": "failed",
          "answer": null,
          "sources": [],
          "error": "A native Logic Apps action failed. Inspect the correlated run."
        }
      },
      "raw": {
        "type": "InitializeVariable",
        "runAfter": {
          "capture_question": [
            "Succeeded"
          ]
        },
        "inputs": {
          "variables": [
            {
              "name": "NativeResponses",
              "type": "string",
              "value": ""
            },
            {
              "name": "Result",
              "type": "object",
              "value": {
                "run_id": "@outputs('capture_question')?['run_id']",
                "route": "unsupported",
                "status": "failed",
                "answer": null,
                "sources": [],
                "error": "A native Logic Apps action failed. Inspect the correlated run."
              }
            }
          ]
        }
      },
      "why": "Jika proses gagal, Result tetap berisi status failed, bukan hasil kosong atau sukses palsu.",
      "scenario": {
        "number": 4,
        "input": {
          "run_id": "<ID_SANDBOX>"
        },
        "output": {
          "NativeResponses": "",
          "Result": {
            "run_id": "<ID_SANDBOX>",
            "route": "unsupported",
            "status": "failed",
            "answer": null,
            "sources": [],
            "error": "A native Logic Apps action failed. Inspect the correlated run."
          }
        },
        "input_kind": "json",
        "output_kind": "json",
        "input_label": "Nilai yang dibaca (contoh)",
        "output_label": "Variabel sesudah (contoh)"
      },
      "purpose": "Membuat dua variabel untuk menampung ID respons dan hasil akhir."
    },
    {
      "id": "Execute",
      "title": "Execute",
      "type": "Scope",
      "group": "Alur contoh TRK001",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Isi",
          "value": [
            "create_conversation",
            "classify_question",
            "record_router_response",
            "Parse_router",
            "invalid_router_result",
            "route_question"
          ]
        }
      ],
      "input": "Tidak memiliki body sendiri.",
      "output": "Status kelompok: Succeeded, Failed, TimedOut atau Skipped.",
      "raw": {
        "type": "Scope",
        "actions": {
          "create_conversation": {
            "type": "Http",
            "inputs": {
              "method": "POST",
              "uri": "<ENDPOINT_FOUNDRY>/openai/v1/conversations",
              "headers": {
                "Foundry-Features": "WorkflowAgents=V1Preview"
              },
              "body": {
                "metadata": {
                  "demo_id": "48254cc6",
                  "run_id": "@outputs('capture_question')?['run_id']",
                  "orchestrator": "logic_apps"
                },
                "items": [
                  {
                    "type": "message",
                    "role": "user",
                    "content": [
                      {
                        "type": "input_text",
                        "text": "@outputs('capture_question')?['question']"
                      }
                    ]
                  }
                ]
              },
              "authentication": {
                "type": "ManagedServiceIdentity",
                "audience": "https://ai.azure.com"
              },
              "retryPolicy": {
                "type": "none"
              }
            },
            "runAfter": {}
          },
          "classify_question": {
            "type": "Http",
            "inputs": {
              "method": "POST",
              "uri": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
              "headers": {
                "Foundry-Features": "WorkflowAgents=V1Preview"
              },
              "body": {
                "input": "@outputs('capture_question')?['question']",
                "stream": false,
                "max_output_tokens": 2048,
                "conversation": "@body('create_conversation')?['id']",
                "agent_reference": {
                  "type": "agent_reference",
                  "name": "kppdemo-router",
                  "version": "1"
                }
              },
              "authentication": {
                "type": "ManagedServiceIdentity",
                "audience": "https://ai.azure.com"
              },
              "retryPolicy": {
                "type": "none"
              }
            },
            "runAfter": {
              "create_conversation": [
                "Succeeded"
              ]
            }
          },
          "record_router_response": {
            "type": "SetVariable",
            "inputs": {
              "name": "NativeResponses",
              "value": "@body('classify_question')?['id']"
            },
            "runAfter": {
              "classify_question": [
                "Succeeded"
              ]
            }
          },
          "Parse_router": {
            "type": "Scope",
            "runAfter": {
              "record_router_response": [
                "Succeeded"
              ]
            },
            "actions": {
              "require_completed_router": {
                "type": "ParseJson",
                "runAfter": {},
                "inputs": {
                  "content": "@body('classify_question')",
                  "schema": {
                    "type": "object",
                    "required": [
                      "status",
                      "output"
                    ],
                    "properties": {
                      "status": {
                        "enum": [
                          "completed"
                        ]
                      },
                      "output": {
                        "type": "array"
                      }
                    }
                  }
                }
              },
              "router_messages": {
                "type": "Query",
                "runAfter": {
                  "require_completed_router": [
                    "Succeeded"
                  ]
                },
                "inputs": {
                  "from": "@body('require_completed_router')?['output']",
                  "where": "@equals(item()?['type'],'message')"
                }
              },
              "router_decision": {
                "type": "ParseJson",
                "runAfter": {
                  "router_messages": [
                    "Succeeded"
                  ]
                },
                "inputs": {
                  "content": "@first(first(body('router_messages'))?['content'])?['text']",
                  "schema": {
                    "type": "object",
                    "required": [
                      "route"
                    ],
                    "additionalProperties": false,
                    "properties": {
                      "route": {
                        "type": "string",
                        "enum": [
                          "mcp",
                          "rest_api",
                          "knowledge",
                          "foundry_iq",
                          "fabric_data",
                          "fabric_iq",
                          "work_iq",
                          "clarification",
                          "unsupported"
                        ]
                      }
                    }
                  }
                }
              }
            }
          },
          "invalid_router_result": {
            "type": "SetVariable",
            "inputs": {
              "name": "Result",
              "value": {
                "run_id": "@outputs('capture_question')?['run_id']",
                "route": "unsupported",
                "status": "failed",
                "answer": null,
                "sources": [],
                "error": "The router returned an unrecognized route. No specialist was invoked."
              }
            },
            "runAfter": {
              "Parse_router": [
                "Failed",
                "TimedOut"
              ]
            }
          },
          "route_question": {
            "type": "Switch",
            "expression": "@body('router_decision')?['route']",
            "cases": {
              "mcp": {
                "case": "mcp",
                "actions": {
                  "mark_mcp": {
                    "type": "Http",
                    "inputs": {
                      "method": "POST",
                      "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
                      "headers": {
                        "Foundry-Features": "WorkflowAgents=V1Preview"
                      },
                      "body": {
                        "items": [
                          {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                              {
                                "type": "output_text",
                                "text": "KPP_ROUTE:mcp"
                              }
                            ]
                          }
                        ]
                      },
                      "authentication": {
                        "type": "ManagedServiceIdentity",
                        "audience": "https://ai.azure.com"
                      },
                      "retryPolicy": {
                        "type": "none"
                      }
                    },
                    "runAfter": {}
                  },
                  "invoke_mcp": {
                    "type": "Http",
                    "inputs": {
                      "method": "POST",
                      "uri": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
                      "headers": {
                        "Foundry-Features": "WorkflowAgents=V1Preview"
                      },
                      "body": {
                        "input": "@outputs('capture_question')?['question']",
                        "stream": false,
                        "max_output_tokens": 2048,
                        "conversation": "@body('create_conversation')?['id']",
                        "agent_reference": {
                          "type": "agent_reference",
                          "name": "kppdemo-mcp",
                          "version": "1"
                        }
                      },
                      "authentication": {
                        "type": "ManagedServiceIdentity",
                        "audience": "https://ai.azure.com"
                      },
                      "retryPolicy": {
                        "type": "none"
                      }
                    },
                    "runAfter": {
                      "mark_mcp": [
                        "Succeeded"
                      ]
                    }
                  },
                  "normalize_mcp": {
                    "type": "Http",
                    "inputs": {
                      "method": "POST",
                      "uri": "<URL_NORMALIZER>",
                      "headers": {},
                      "body": {
                        "run_id": "@outputs('capture_question')?['run_id']",
                        "route": "mcp",
                        "response": "@body('invoke_mcp')"
                      },
                      "authentication": {
                        "type": "ManagedServiceIdentity",
                        "audience": "<AUDIENCE_API>"
                      },
                      "retryPolicy": {
                        "type": "none"
                      }
                    },
                    "runAfter": {
                      "invoke_mcp": [
                        "Succeeded"
                      ]
                    }
                  },
                  "record_mcp_response": {
                    "type": "SetVariable",
                    "inputs": {
                      "name": "NativeResponses",
                      "value": "@concat(body('classify_question')?['id'],',',body('invoke_mcp')?['id'])"
                    },
                    "runAfter": {
                      "normalize_mcp": [
                        "Succeeded"
                      ]
                    }
                  },
                  "set_result_mcp": {
                    "type": "SetVariable",
                    "inputs": {
                      "name": "Result",
                      "value": "@body('normalize_mcp')"
                    },
                    "runAfter": {
                      "record_mcp_response": [
                        "Succeeded"
                      ]
                    }
                  }
                }
              },
              "rest_api": {
                "case": "rest_api",
                "actions": {
                  "mark_rest_api": {
                    "type": "Http",
                    "inputs": {
                      "method": "POST",
                      "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
                      "headers": {
                        "Foundry-Features": "WorkflowAgents=V1Preview"
                      },
                      "body": {
                        "items": [
                          {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                              {
                                "type": "output_text",
                                "text": "KPP_ROUTE:rest_api"
                              }
                            ]
                          }
                        ]
                      },
                      "authentication": {
                        "type": "ManagedServiceIdentity",
                        "audience": "https://ai.azure.com"
                      },
                      "retryPolicy": {
                        "type": "none"
                      }
                    },
                    "runAfter": {}
                  },
                  "invoke_rest_api": {
                    "type": "Http",
                    "inputs": {
                      "method": "POST",
                      "uri": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
                      "headers": {
                        "Foundry-Features": "WorkflowAgents=V1Preview"
                      },
                      "body": {
                        "input": "@outputs('capture_question')?['question']",
                        "stream": false,
                        "max_output_tokens": 2048,
                        "conversation": "@body('create_conversation')?['id']",
                        "agent_reference": {
                          "type": "agent_reference",
                          "name": "kppdemo-rest",
                          "version": "4"
                        }
                      },
                      "authentication": {
                        "type": "ManagedServiceIdentity",
                        "audience": "https://ai.azure.com"
                      },
                      "retryPolicy": {
                        "type": "none"
                      }
                    },
                    "runAfter": {
                      "mark_rest_api": [
                        "Succeeded"
                      ]
                    }
                  },
                  "normalize_rest_api": {
                    "type": "Http",
                    "inputs": {
                      "method": "POST",
                      "uri": "<URL_NORMALIZER>",
                      "headers": {},
                      "body": {
                        "run_id": "@outputs('capture_question')?['run_id']",
                        "route": "rest_api",
                        "response": "@body('invoke_rest_api')"
                      },
                      "authentication": {
                        "type": "ManagedServiceIdentity",
                        "audience": "<AUDIENCE_API>"
                      },
                      "retryPolicy": {
                        "type": "none"
                      }
                    },
                    "runAfter": {
                      "invoke_rest_api": [
                        "Succeeded"
                      ]
                    }
                  },
                  "record_rest_api_response": {
                    "type": "SetVariable",
                    "inputs": {
                      "name": "NativeResponses",
                      "value": "@concat(body('classify_question')?['id'],',',body('invoke_rest_api')?['id'])"
                    },
                    "runAfter": {
                      "normalize_rest_api": [
                        "Succeeded"
                      ]
                    }
                  },
                  "set_result_rest_api": {
                    "type": "SetVariable",
                    "inputs": {
                      "name": "Result",
                      "value": "@body('normalize_rest_api')"
                    },
                    "runAfter": {
                      "record_rest_api_response": [
                        "Succeeded"
                      ]
                    }
                  }
                }
              },
              "knowledge": {
                "case": "knowledge",
                "actions": {
                  "mark_knowledge": {
                    "type": "Http",
                    "inputs": {
                      "method": "POST",
                      "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
                      "headers": {
                        "Foundry-Features": "WorkflowAgents=V1Preview"
                      },
                      "body": {
                        "items": [
                          {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                              {
                                "type": "output_text",
                                "text": "KPP_ROUTE:knowledge"
                              }
                            ]
                          }
                        ]
                      },
                      "authentication": {
                        "type": "ManagedServiceIdentity",
                        "audience": "https://ai.azure.com"
                      },
                      "retryPolicy": {
                        "type": "none"
                      }
                    },
                    "runAfter": {}
                  },
                  "invoke_knowledge": {
                    "type": "Http",
                    "inputs": {
                      "method": "POST",
                      "uri": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
                      "headers": {
                        "Foundry-Features": "WorkflowAgents=V1Preview"
                      },
                      "body": {
                        "input": "@outputs('capture_question')?['question']",
                        "stream": false,
                        "max_output_tokens": 2048,
                        "conversation": "@body('create_conversation')?['id']",
                        "agent_reference": {
                          "type": "agent_reference",
                          "name": "kppdemo-knowledge",
                          "version": "2"
                        }
                      },
                      "authentication": {
                        "type": "ManagedServiceIdentity",
                        "audience": "https://ai.azure.com"
                      },
                      "retryPolicy": {
                        "type": "none"
                      }
                    },
                    "runAfter": {
                      "mark_knowledge": [
                        "Succeeded"
                      ]
                    }
                  },
                  "normalize_knowledge": {
                    "type": "Http",
                    "inputs": {
                      "method": "POST",
                      "uri": "<URL_NORMALIZER>",
                      "headers": {},
                      "body": {
                        "run_id": "@outputs('capture_question')?['run_id']",
                        "route": "knowledge",
                        "response": "@body('invoke_knowledge')"
                      },
                      "authentication": {
                        "type": "ManagedServiceIdentity",
                        "audience": "<AUDIENCE_API>"
                      },
                      "retryPolicy": {
                        "type": "none"
                      }
                    },
                    "runAfter": {
                      "invoke_knowledge": [
                        "Succeeded"
                      ]
                    }
                  },
                  "record_knowledge_response": {
                    "type": "SetVariable",
                    "inputs": {
                      "name": "NativeResponses",
                      "value": "@concat(body('classify_question')?['id'],',',body('invoke_knowledge')?['id'])"
                    },
                    "runAfter": {
                      "normalize_knowledge": [
                        "Succeeded"
                      ]
                    }
                  },
                  "set_result_knowledge": {
                    "type": "SetVariable",
                    "inputs": {
                      "name": "Result",
                      "value": "@body('normalize_knowledge')"
                    },
                    "runAfter": {
                      "record_knowledge_response": [
                        "Succeeded"
                      ]
                    }
                  }
                }
              },
              "foundry_iq": {
                "case": "foundry_iq",
                "actions": {
                  "mark_foundry_iq": {
                    "type": "Http",
                    "inputs": {
                      "method": "POST",
                      "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
                      "headers": {
                        "Foundry-Features": "WorkflowAgents=V1Preview"
                      },
                      "body": {
                        "items": [
                          {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                              {
                                "type": "output_text",
                                "text": "KPP_ROUTE:foundry_iq"
                              }
                            ]
                          }
                        ]
                      },
                      "authentication": {
                        "type": "ManagedServiceIdentity",
                        "audience": "https://ai.azure.com"
                      },
                      "retryPolicy": {
                        "type": "none"
                      }
                    },
                    "runAfter": {}
                  },
                  "invoke_foundry_iq": {
                    "type": "Http",
                    "inputs": {
                      "method": "POST",
                      "uri": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
                      "headers": {
                        "Foundry-Features": "WorkflowAgents=V1Preview"
                      },
                      "body": {
                        "input": "@outputs('capture_question')?['question']",
                        "stream": false,
                        "max_output_tokens": 2048,
                        "conversation": "@body('create_conversation')?['id']",
                        "agent_reference": {
                          "type": "agent_reference",
                          "name": "kppdemo-foundry-iq",
                          "version": "2"
                        }
                      },
                      "authentication": {
                        "type": "ManagedServiceIdentity",
                        "audience": "https://ai.azure.com"
                      },
                      "retryPolicy": {
                        "type": "none"
                      }
                    },
                    "runAfter": {
                      "mark_foundry_iq": [
                        "Succeeded"
                      ]
                    }
                  },
                  "normalize_foundry_iq": {
                    "type": "Http",
                    "inputs": {
                      "method": "POST",
                      "uri": "<URL_NORMALIZER>",
                      "headers": {},
                      "body": {
                        "run_id": "@outputs('capture_question')?['run_id']",
                        "route": "foundry_iq",
                        "response": "@body('invoke_foundry_iq')"
                      },
                      "authentication": {
                        "type": "ManagedServiceIdentity",
                        "audience": "<AUDIENCE_API>"
                      },
                      "retryPolicy": {
                        "type": "none"
                      }
                    },
                    "runAfter": {
                      "invoke_foundry_iq": [
                        "Succeeded"
                      ]
                    }
                  },
                  "record_foundry_iq_response": {
                    "type": "SetVariable",
                    "inputs": {
                      "name": "NativeResponses",
                      "value": "@concat(body('classify_question')?['id'],',',body('invoke_foundry_iq')?['id'])"
                    },
                    "runAfter": {
                      "normalize_foundry_iq": [
                        "Succeeded"
                      ]
                    }
                  },
                  "set_result_foundry_iq": {
                    "type": "SetVariable",
                    "inputs": {
                      "name": "Result",
                      "value": "@body('normalize_foundry_iq')"
                    },
                    "runAfter": {
                      "record_foundry_iq_response": [
                        "Succeeded"
                      ]
                    }
                  }
                }
              },
              "fabric_data": {
                "case": "fabric_data",
                "actions": {
                  "mark_fabric_data": {
                    "type": "Http",
                    "inputs": {
                      "method": "POST",
                      "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
                      "headers": {
                        "Foundry-Features": "WorkflowAgents=V1Preview"
                      },
                      "body": {
                        "items": [
                          {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                              {
                                "type": "output_text",
                                "text": "KPP_ROUTE:fabric_data"
                              }
                            ]
                          }
                        ]
                      },
                      "authentication": {
                        "type": "ManagedServiceIdentity",
                        "audience": "https://ai.azure.com"
                      },
                      "retryPolicy": {
                        "type": "none"
                      }
                    },
                    "runAfter": {}
                  },
                  "invoke_fabric_data": {
                    "type": "Http",
                    "inputs": {
                      "method": "POST",
                      "uri": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
                      "headers": {
                        "Foundry-Features": "WorkflowAgents=V1Preview"
                      },
                      "body": {
                        "input": "@outputs('capture_question')?['question']",
                        "stream": false,
                        "max_output_tokens": 2048,
                        "conversation": "@body('create_conversation')?['id']",
                        "agent_reference": {
                          "type": "agent_reference",
                          "name": "kppdemo-fabric-data",
                          "version": "1"
                        }
                      },
                      "authentication": {
                        "type": "ManagedServiceIdentity",
                        "audience": "https://ai.azure.com"
                      },
                      "retryPolicy": {
                        "type": "none"
                      }
                    },
                    "runAfter": {
                      "mark_fabric_data": [
                        "Succeeded"
                      ]
                    }
                  },
                  "normalize_fabric_data": {
                    "type": "Http",
                    "inputs": {
                      "method": "POST",
                      "uri": "<URL_NORMALIZER>",
                      "headers": {},
                      "body": {
                        "run_id": "@outputs('capture_question')?['run_id']",
                        "route": "fabric_data",
                        "response": "@body('invoke_fabric_data')"
                      },
                      "authentication": {
                        "type": "ManagedServiceIdentity",
                        "audience": "<AUDIENCE_API>"
                      },
                      "retryPolicy": {
                        "type": "none"
                      }
                    },
                    "runAfter": {
                      "invoke_fabric_data": [
                        "Succeeded"
                      ]
                    }
                  },
                  "record_fabric_data_response": {
                    "type": "SetVariable",
                    "inputs": {
                      "name": "NativeResponses",
                      "value": "@concat(body('classify_question')?['id'],',',body('invoke_fabric_data')?['id'])"
                    },
                    "runAfter": {
                      "normalize_fabric_data": [
                        "Succeeded"
                      ]
                    }
                  },
                  "set_result_fabric_data": {
                    "type": "SetVariable",
                    "inputs": {
                      "name": "Result",
                      "value": "@body('normalize_fabric_data')"
                    },
                    "runAfter": {
                      "record_fabric_data_response": [
                        "Succeeded"
                      ]
                    }
                  }
                }
              },
              "fabric_iq": {
                "case": "fabric_iq",
                "actions": {
                  "blocked_fabric_iq": {
                    "type": "Http",
                    "inputs": {
                      "method": "POST",
                      "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
                      "headers": {
                        "Foundry-Features": "WorkflowAgents=V1Preview"
                      },
                      "body": {
                        "items": [
                          {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                              {
                                "type": "output_text",
                                "text": "KPP_ROUTE:fabric_iq\nKPP_STATUS:blocked\nNative Fabric ontology is unavailable: FeatureNotAvailable."
                              }
                            ]
                          }
                        ]
                      },
                      "authentication": {
                        "type": "ManagedServiceIdentity",
                        "audience": "https://ai.azure.com"
                      },
                      "retryPolicy": {
                        "type": "none"
                      }
                    },
                    "runAfter": {}
                  },
                  "set_result_fabric_iq": {
                    "type": "SetVariable",
                    "inputs": {
                      "name": "Result",
                      "value": {
                        "run_id": "@outputs('capture_question')?['run_id']",
                        "route": "fabric_iq",
                        "status": "blocked",
                        "answer": null,
                        "sources": [],
                        "error": "Native Fabric ontology is unavailable: FeatureNotAvailable."
                      }
                    },
                    "runAfter": {
                      "blocked_fabric_iq": [
                        "Succeeded"
                      ]
                    }
                  }
                }
              },
              "work_iq": {
                "case": "work_iq",
                "actions": {
                  "blocked_work_iq": {
                    "type": "Http",
                    "inputs": {
                      "method": "POST",
                      "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
                      "headers": {
                        "Foundry-Features": "WorkflowAgents=V1Preview"
                      },
                      "body": {
                        "items": [
                          {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                              {
                                "type": "output_text",
                                "text": "KPP_ROUTE:work_iq\nKPP_STATUS:blocked\nA separate Work IQ sandbox has not been supplied. No workplace data was accessed."
                              }
                            ]
                          }
                        ]
                      },
                      "authentication": {
                        "type": "ManagedServiceIdentity",
                        "audience": "https://ai.azure.com"
                      },
                      "retryPolicy": {
                        "type": "none"
                      }
                    },
                    "runAfter": {}
                  },
                  "set_result_work_iq": {
                    "type": "SetVariable",
                    "inputs": {
                      "name": "Result",
                      "value": {
                        "run_id": "@outputs('capture_question')?['run_id']",
                        "route": "work_iq",
                        "status": "blocked",
                        "answer": null,
                        "sources": [],
                        "error": "A separate Work IQ sandbox has not been supplied. No workplace data was accessed."
                      }
                    },
                    "runAfter": {
                      "blocked_work_iq": [
                        "Succeeded"
                      ]
                    }
                  }
                }
              },
              "clarification": {
                "case": "clarification",
                "actions": {
                  "ask_clarification": {
                    "type": "Http",
                    "inputs": {
                      "method": "POST",
                      "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
                      "headers": {
                        "Foundry-Features": "WorkflowAgents=V1Preview"
                      },
                      "body": {
                        "items": [
                          {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                              {
                                "type": "output_text",
                                "text": "KPP_ROUTE:clarification\nKPP_STATUS:clarification\nPlease specify one topic: production, maintenance, stock, document lookup, or native knowledge retrieval."
                              }
                            ]
                          }
                        ]
                      },
                      "authentication": {
                        "type": "ManagedServiceIdentity",
                        "audience": "https://ai.azure.com"
                      },
                      "retryPolicy": {
                        "type": "none"
                      }
                    },
                    "runAfter": {}
                  },
                  "set_result_clarification": {
                    "type": "SetVariable",
                    "inputs": {
                      "name": "Result",
                      "value": {
                        "run_id": "@outputs('capture_question')?['run_id']",
                        "route": "clarification",
                        "status": "clarification",
                        "answer": "Please specify one topic: production, maintenance, stock, document lookup, or native knowledge retrieval.",
                        "sources": [],
                        "error": null
                      }
                    },
                    "runAfter": {
                      "ask_clarification": [
                        "Succeeded"
                      ]
                    }
                  }
                }
              },
              "unsupported": {
                "case": "unsupported",
                "actions": {
                  "reject_unsupported": {
                    "type": "Http",
                    "inputs": {
                      "method": "POST",
                      "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
                      "headers": {
                        "Foundry-Features": "WorkflowAgents=V1Preview"
                      },
                      "body": {
                        "items": [
                          {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                              {
                                "type": "output_text",
                                "text": "KPP_ROUTE:unsupported\nKPP_STATUS:unsupported\nOnly read-only questions about the new synthetic mining demo are supported. Live systems and writes are not accessed."
                              }
                            ]
                          }
                        ]
                      },
                      "authentication": {
                        "type": "ManagedServiceIdentity",
                        "audience": "https://ai.azure.com"
                      },
                      "retryPolicy": {
                        "type": "none"
                      }
                    },
                    "runAfter": {}
                  },
                  "set_result_unsupported": {
                    "type": "SetVariable",
                    "inputs": {
                      "name": "Result",
                      "value": {
                        "run_id": "@outputs('capture_question')?['run_id']",
                        "route": "unsupported",
                        "status": "unsupported",
                        "answer": "Only read-only questions about the new synthetic mining demo are supported. Live systems and writes are not accessed.",
                        "sources": [],
                        "error": null
                      }
                    },
                    "runAfter": {
                      "reject_unsupported": [
                        "Succeeded"
                      ]
                    }
                  }
                }
              }
            },
            "default": {
              "actions": {
                "default_invalid_route": {
                  "type": "SetVariable",
                  "inputs": {
                    "name": "Result",
                    "value": {
                      "run_id": "@outputs('capture_question')?['run_id']",
                      "route": "unsupported",
                      "status": "failed",
                      "answer": null,
                      "sources": [],
                      "error": "The router returned an unrecognized route. No specialist was invoked."
                    }
                  },
                  "runAfter": {}
                }
              }
            },
            "runAfter": {
              "Parse_router": [
                "Succeeded"
              ]
            }
          }
        },
        "runAfter": {
          "Initialize_result": [
            "Succeeded"
          ]
        }
      },
      "why": "Scope selesai setelah action di dalamnya selesai; nilai yang tersedia berasal dari node anak, bukan body Scope.",
      "scenario": {
        "number": 5,
        "input": {
          "capture_question": {
            "question": "Show work orders for equipment TRK001.",
            "run_id": "<ID_SANDBOX>"
          },
          "NativeResponses": "",
          "Result": {
            "run_id": "<ID_SANDBOX>",
            "route": "unsupported",
            "status": "failed",
            "answer": null,
            "sources": [],
            "error": "A native Logic Apps action failed. Inspect the correlated run."
          }
        },
        "output": {
          "NativeResponses": "resp_contoh,resp_mcp_contoh",
          "Result": {
            "run_id": "<ID_SANDBOX>",
            "route": "mcp",
            "status": "success",
            "answer": "Work order WO001 for equipment TRK001 is open, with priority demo-high.",
            "sources": [
              {
                "kind": "demo_fixture",
                "id": "urn:kppdemo:maintenance/TRK001"
              }
            ],
            "error": null
          }
        },
        "input_kind": "json",
        "output_kind": "json",
        "input_label": "Nilai tersedia; bukan body Scope",
        "output_label": "Nilai sesudah Scope; bukan body Scope"
      },
      "purpose": "Mengelompokkan proses utama."
    },
    {
      "id": "create_conversation",
      "title": "create conversation",
      "type": "Http",
      "group": "Alur contoh TRK001",
      "url": "<ENDPOINT_FOUNDRY>/openai/v1/conversations",
      "url_note": "",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "https://ai.azure.com"
        },
        {
          "name": "Foundry-Features",
          "value": "WorkflowAgents=V1Preview"
        }
      ],
      "input": {
        "metadata": {
          "demo_id": "48254cc6",
          "run_id": "@outputs('capture_question')?['run_id']",
          "orchestrator": "logic_apps"
        },
        "items": [
          {
            "type": "message",
            "role": "user",
            "content": [
              {
                "type": "input_text",
                "text": "@outputs('capture_question')?['question']"
              }
            ]
          }
        ]
      },
      "output": {
        "id": "conv_contoh"
      },
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "<ENDPOINT_FOUNDRY>/openai/v1/conversations",
          "headers": {
            "Foundry-Features": "WorkflowAgents=V1Preview"
          },
          "body": {
            "metadata": {
              "demo_id": "48254cc6",
              "run_id": "@outputs('capture_question')?['run_id']",
              "orchestrator": "logic_apps"
            },
            "items": [
              {
                "type": "message",
                "role": "user",
                "content": [
                  {
                    "type": "input_text",
                    "text": "@outputs('capture_question')?['question']"
                  }
                ]
              }
            ]
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "https://ai.azure.com"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {}
      },
      "why": "Router dan specialist memakai conversation yang sama agar riwayat request tetap tersambung.",
      "scenario": {
        "number": 6,
        "input": {
          "metadata": {
            "demo_id": "48254cc6",
            "run_id": "<ID_SANDBOX>",
            "orchestrator": "logic_apps"
          },
          "items": [
            {
              "type": "message",
              "role": "user",
              "content": [
                {
                  "type": "input_text",
                  "text": "Show work orders for equipment TRK001."
                }
              ]
            }
          ]
        },
        "output": {
          "id": "conv_contoh"
        },
        "input_kind": "json",
        "output_kind": "json",
        "input_label": "Body dikirim (contoh)",
        "output_label": "Output (contoh)"
      },
      "purpose": "Membuat conversation untuk router dan specialist."
    },
    {
      "id": "classify_question",
      "title": "classify question",
      "type": "Http",
      "group": "Alur contoh TRK001",
      "url": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
      "url_note": "API project Foundry, bukan URL satu agent. Agent dipilih lewat agent_reference.name dan version pada body.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "https://ai.azure.com"
        },
        {
          "name": "Foundry-Features",
          "value": "WorkflowAgents=V1Preview"
        },
        {
          "name": "Agent",
          "value": "kppdemo-router:1"
        }
      ],
      "input": {
        "input": "@outputs('capture_question')?['question']",
        "stream": false,
        "max_output_tokens": 2048,
        "conversation": "@body('create_conversation')?['id']",
        "agent_reference": {
          "type": "agent_reference",
          "name": "kppdemo-router",
          "version": "1"
        }
      },
      "output": {
        "id": "resp_contoh",
        "status": "completed",
        "output": [
          {
            "type": "message",
            "content": [
              {
                "type": "output_text",
                "text": "{\"route\":\"mcp\"}"
              }
            ]
          }
        ]
      },
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
          "headers": {
            "Foundry-Features": "WorkflowAgents=V1Preview"
          },
          "body": {
            "input": "@outputs('capture_question')?['question']",
            "stream": false,
            "max_output_tokens": 2048,
            "conversation": "@body('create_conversation')?['id']",
            "agent_reference": {
              "type": "agent_reference",
              "name": "kppdemo-router",
              "version": "1"
            }
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "https://ai.azure.com"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {
          "create_conversation": [
            "Succeeded"
          ]
        }
      },
      "why": "Work order harus diarahkan ke MCP, bukan ke stok REST atau pencarian dokumen.",
      "scenario": {
        "number": 7,
        "input": {
          "input": "Show work orders for equipment TRK001.",
          "stream": false,
          "max_output_tokens": 2048,
          "conversation": "conv_contoh",
          "agent_reference": {
            "type": "agent_reference",
            "name": "kppdemo-router",
            "version": "1"
          }
        },
        "output": {
          "id": "resp_contoh",
          "status": "completed",
          "output": [
            {
              "type": "message",
              "content": [
                {
                  "type": "output_text",
                  "text": "{\"route\":\"mcp\"}"
                }
              ]
            }
          ]
        },
        "input_kind": "json",
        "output_kind": "json",
        "input_label": "Body dikirim (contoh)",
        "output_label": "Output (contoh)"
      },
      "purpose": "Meminta router menentukan route pertanyaan."
    },
    {
      "id": "record_router_response",
      "title": "record router response",
      "type": "SetVariable",
      "group": "Alur contoh TRK001",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Name",
          "value": "NativeResponses"
        },
        {
          "name": "Value",
          "value": "@body('classify_question')?['id']"
        }
      ],
      "input": "ID respons dari classify_question.",
      "output": "resp_contoh",
      "raw": {
        "type": "SetVariable",
        "inputs": {
          "name": "NativeResponses",
          "value": "@body('classify_question')?['id']"
        },
        "runAfter": {
          "classify_question": [
            "Succeeded"
          ]
        }
      },
      "why": "ID respons disimpan supaya hasil UI bisa ditelusuri ke respons router dan specialist di Foundry.",
      "scenario": {
        "number": 8,
        "input": "resp_contoh",
        "output": {
          "NativeResponses": "resp_contoh"
        },
        "input_kind": "json",
        "output_kind": "json",
        "input_label": "Nilai yang dibaca (contoh)",
        "output_label": "Variabel sesudah (contoh)"
      },
      "purpose": "Mencatat ID respons agent ke NativeResponses."
    },
    {
      "id": "Parse_router",
      "title": "Parse router",
      "type": "Scope",
      "group": "Alur contoh TRK001",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Isi",
          "value": [
            "require_completed_router",
            "router_messages",
            "router_decision"
          ]
        }
      ],
      "input": "Tidak memiliki body sendiri.",
      "output": "Status kelompok: Succeeded, Failed, TimedOut atau Skipped.",
      "raw": {
        "type": "Scope",
        "runAfter": {
          "record_router_response": [
            "Succeeded"
          ]
        },
        "actions": {
          "require_completed_router": {
            "type": "ParseJson",
            "runAfter": {},
            "inputs": {
              "content": "@body('classify_question')",
              "schema": {
                "type": "object",
                "required": [
                  "status",
                  "output"
                ],
                "properties": {
                  "status": {
                    "enum": [
                      "completed"
                    ]
                  },
                  "output": {
                    "type": "array"
                  }
                }
              }
            }
          },
          "router_messages": {
            "type": "Query",
            "runAfter": {
              "require_completed_router": [
                "Succeeded"
              ]
            },
            "inputs": {
              "from": "@body('require_completed_router')?['output']",
              "where": "@equals(item()?['type'],'message')"
            }
          },
          "router_decision": {
            "type": "ParseJson",
            "runAfter": {
              "router_messages": [
                "Succeeded"
              ]
            },
            "inputs": {
              "content": "@first(first(body('router_messages'))?['content'])?['text']",
              "schema": {
                "type": "object",
                "required": [
                  "route"
                ],
                "additionalProperties": false,
                "properties": {
                  "route": {
                    "type": "string",
                    "enum": [
                      "mcp",
                      "rest_api",
                      "knowledge",
                      "foundry_iq",
                      "fabric_data",
                      "fabric_iq",
                      "work_iq",
                      "clarification",
                      "unsupported"
                    ]
                  }
                }
              }
            }
          }
        }
      },
      "why": "Scope selesai setelah action di dalamnya selesai; nilai yang tersedia berasal dari node anak, bukan body Scope.",
      "scenario": {
        "number": 9,
        "input": {
          "id": "resp_contoh",
          "status": "completed",
          "output": [
            {
              "type": "message",
              "content": [
                {
                  "type": "output_text",
                  "text": "{\"route\":\"mcp\"}"
                }
              ]
            }
          ]
        },
        "output": {
          "route": "mcp"
        },
        "input_kind": "json",
        "output_kind": "json",
        "input_label": "Nilai tersedia; bukan body Scope",
        "output_label": "Nilai sesudah Scope; bukan body Scope"
      },
      "purpose": "Mengelompokkan pemeriksaan respons router."
    },
    {
      "id": "require_completed_router",
      "title": "require completed router",
      "type": "ParseJson",
      "group": "Alur contoh TRK001",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Content",
          "value": "@body('classify_question')"
        },
        {
          "name": "status",
          "value": "Pilihan: completed; wajib"
        },
        {
          "name": "output",
          "value": "array; wajib"
        }
      ],
      "input": "@body('classify_question')",
      "output": "Object respons router yang lolos pemeriksaan.",
      "raw": {
        "type": "ParseJson",
        "runAfter": {},
        "inputs": {
          "content": "@body('classify_question')",
          "schema": {
            "type": "object",
            "required": [
              "status",
              "output"
            ],
            "properties": {
              "status": {
                "enum": [
                  "completed"
                ]
              },
              "output": {
                "type": "array"
              }
            }
          }
        }
      },
      "why": "Route dari respons yang gagal atau belum selesai tidak boleh dipakai untuk memilih specialist.",
      "scenario": {
        "number": 10,
        "input": {
          "id": "resp_contoh",
          "status": "completed",
          "output": [
            {
              "type": "message",
              "content": [
                {
                  "type": "output_text",
                  "text": "{\"route\":\"mcp\"}"
                }
              ]
            }
          ]
        },
        "output": {
          "id": "resp_contoh",
          "status": "completed",
          "output": [
            {
              "type": "message",
              "content": [
                {
                  "type": "output_text",
                  "text": "{\"route\":\"mcp\"}"
                }
              ]
            }
          ]
        },
        "input_kind": "json",
        "output_kind": "json",
        "input_label": "Nilai masuk (contoh)",
        "output_label": "Output (contoh)"
      },
      "purpose": "Memastikan router sudah completed dan output-nya berupa array."
    },
    {
      "id": "router_messages",
      "title": "router messages",
      "type": "Query",
      "group": "Alur contoh TRK001",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "From",
          "value": "@body('require_completed_router')?['output']"
        },
        {
          "name": "Filter",
          "value": "@equals(item()?['type'],'message')"
        }
      ],
      "input": "@body('require_completed_router')?['output']",
      "output": [
        {
          "type": "message",
          "content": [
            {
              "type": "output_text",
              "text": "{\"route\":\"mcp\"}"
            }
          ]
        }
      ],
      "raw": {
        "type": "Query",
        "runAfter": {
          "require_completed_router": [
            "Succeeded"
          ]
        },
        "inputs": {
          "from": "@body('require_completed_router')?['output']",
          "where": "@equals(item()?['type'],'message')"
        }
      },
      "why": "Output router bisa berisi beberapa jenis item; hanya message yang berisi teks keputusan.",
      "scenario": {
        "number": 11,
        "input": [
          {
            "type": "message",
            "content": [
              {
                "type": "output_text",
                "text": "{\"route\":\"mcp\"}"
              }
            ]
          }
        ],
        "output": [
          {
            "type": "message",
            "content": [
              {
                "type": "output_text",
                "text": "{\"route\":\"mcp\"}"
              }
            ]
          }
        ],
        "input_kind": "json",
        "output_kind": "json",
        "input_label": "Nilai masuk (contoh)",
        "output_label": "Output (contoh)"
      },
      "purpose": "Mengambil hanya item message dari output router."
    },
    {
      "id": "router_decision",
      "title": "router decision",
      "type": "ParseJson",
      "group": "Alur contoh TRK001",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Content",
          "value": "@first(first(body('router_messages'))?['content'])?['text']"
        },
        {
          "name": "route",
          "value": "Pilihan: mcp, rest_api, knowledge, foundry_iq, fabric_data, fabric_iq, work_iq, clarification, unsupported; wajib"
        },
        {
          "name": "Field tambahan",
          "value": "Ditolak"
        }
      ],
      "input": "@first(first(body('router_messages'))?['content'])?['text']",
      "output": {
        "route": "mcp"
      },
      "raw": {
        "type": "ParseJson",
        "runAfter": {
          "router_messages": [
            "Succeeded"
          ]
        },
        "inputs": {
          "content": "@first(first(body('router_messages'))?['content'])?['text']",
          "schema": {
            "type": "object",
            "required": [
              "route"
            ],
            "additionalProperties": false,
            "properties": {
              "route": {
                "type": "string",
                "enum": [
                  "mcp",
                  "rest_api",
                  "knowledge",
                  "foundry_iq",
                  "fabric_data",
                  "fabric_iq",
                  "work_iq",
                  "clarification",
                  "unsupported"
                ]
              }
            }
          }
        }
      },
      "why": "Router mengirim teks {\"route\":\"mcp\"}; Switch perlu object yang field route-nya bisa dibaca.",
      "scenario": {
        "number": 12,
        "input": "{\"route\":\"mcp\"}",
        "output": {
          "route": "mcp"
        },
        "input_kind": "text",
        "output_kind": "json",
        "input_label": "Teks JSON masuk (contoh)",
        "output_label": "Output (contoh)"
      },
      "purpose": "Mengubah teks JSON router menjadi object route."
    },
    {
      "id": "route_question",
      "title": "route question",
      "type": "Switch",
      "group": "Alur contoh TRK001",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "On",
          "value": "@body('router_decision')?['route']"
        },
        {
          "name": "Case",
          "value": [
            "mcp",
            "rest_api",
            "knowledge",
            "foundry_iq",
            "fabric_data",
            "fabric_iq",
            "work_iq",
            "clarification",
            "unsupported"
          ]
        }
      ],
      "input": {
        "route": "mcp"
      },
      "output": "Pada contoh ini, case mcp berjalan. Case lain dilewati.",
      "raw": {
        "type": "Switch",
        "expression": "@body('router_decision')?['route']",
        "cases": {
          "mcp": {
            "case": "mcp",
            "actions": {
              "mark_mcp": {
                "type": "Http",
                "inputs": {
                  "method": "POST",
                  "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
                  "headers": {
                    "Foundry-Features": "WorkflowAgents=V1Preview"
                  },
                  "body": {
                    "items": [
                      {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                          {
                            "type": "output_text",
                            "text": "KPP_ROUTE:mcp"
                          }
                        ]
                      }
                    ]
                  },
                  "authentication": {
                    "type": "ManagedServiceIdentity",
                    "audience": "https://ai.azure.com"
                  },
                  "retryPolicy": {
                    "type": "none"
                  }
                },
                "runAfter": {}
              },
              "invoke_mcp": {
                "type": "Http",
                "inputs": {
                  "method": "POST",
                  "uri": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
                  "headers": {
                    "Foundry-Features": "WorkflowAgents=V1Preview"
                  },
                  "body": {
                    "input": "@outputs('capture_question')?['question']",
                    "stream": false,
                    "max_output_tokens": 2048,
                    "conversation": "@body('create_conversation')?['id']",
                    "agent_reference": {
                      "type": "agent_reference",
                      "name": "kppdemo-mcp",
                      "version": "1"
                    }
                  },
                  "authentication": {
                    "type": "ManagedServiceIdentity",
                    "audience": "https://ai.azure.com"
                  },
                  "retryPolicy": {
                    "type": "none"
                  }
                },
                "runAfter": {
                  "mark_mcp": [
                    "Succeeded"
                  ]
                }
              },
              "normalize_mcp": {
                "type": "Http",
                "inputs": {
                  "method": "POST",
                  "uri": "<URL_NORMALIZER>",
                  "headers": {},
                  "body": {
                    "run_id": "@outputs('capture_question')?['run_id']",
                    "route": "mcp",
                    "response": "@body('invoke_mcp')"
                  },
                  "authentication": {
                    "type": "ManagedServiceIdentity",
                    "audience": "<AUDIENCE_API>"
                  },
                  "retryPolicy": {
                    "type": "none"
                  }
                },
                "runAfter": {
                  "invoke_mcp": [
                    "Succeeded"
                  ]
                }
              },
              "record_mcp_response": {
                "type": "SetVariable",
                "inputs": {
                  "name": "NativeResponses",
                  "value": "@concat(body('classify_question')?['id'],',',body('invoke_mcp')?['id'])"
                },
                "runAfter": {
                  "normalize_mcp": [
                    "Succeeded"
                  ]
                }
              },
              "set_result_mcp": {
                "type": "SetVariable",
                "inputs": {
                  "name": "Result",
                  "value": "@body('normalize_mcp')"
                },
                "runAfter": {
                  "record_mcp_response": [
                    "Succeeded"
                  ]
                }
              }
            }
          },
          "rest_api": {
            "case": "rest_api",
            "actions": {
              "mark_rest_api": {
                "type": "Http",
                "inputs": {
                  "method": "POST",
                  "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
                  "headers": {
                    "Foundry-Features": "WorkflowAgents=V1Preview"
                  },
                  "body": {
                    "items": [
                      {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                          {
                            "type": "output_text",
                            "text": "KPP_ROUTE:rest_api"
                          }
                        ]
                      }
                    ]
                  },
                  "authentication": {
                    "type": "ManagedServiceIdentity",
                    "audience": "https://ai.azure.com"
                  },
                  "retryPolicy": {
                    "type": "none"
                  }
                },
                "runAfter": {}
              },
              "invoke_rest_api": {
                "type": "Http",
                "inputs": {
                  "method": "POST",
                  "uri": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
                  "headers": {
                    "Foundry-Features": "WorkflowAgents=V1Preview"
                  },
                  "body": {
                    "input": "@outputs('capture_question')?['question']",
                    "stream": false,
                    "max_output_tokens": 2048,
                    "conversation": "@body('create_conversation')?['id']",
                    "agent_reference": {
                      "type": "agent_reference",
                      "name": "kppdemo-rest",
                      "version": "4"
                    }
                  },
                  "authentication": {
                    "type": "ManagedServiceIdentity",
                    "audience": "https://ai.azure.com"
                  },
                  "retryPolicy": {
                    "type": "none"
                  }
                },
                "runAfter": {
                  "mark_rest_api": [
                    "Succeeded"
                  ]
                }
              },
              "normalize_rest_api": {
                "type": "Http",
                "inputs": {
                  "method": "POST",
                  "uri": "<URL_NORMALIZER>",
                  "headers": {},
                  "body": {
                    "run_id": "@outputs('capture_question')?['run_id']",
                    "route": "rest_api",
                    "response": "@body('invoke_rest_api')"
                  },
                  "authentication": {
                    "type": "ManagedServiceIdentity",
                    "audience": "<AUDIENCE_API>"
                  },
                  "retryPolicy": {
                    "type": "none"
                  }
                },
                "runAfter": {
                  "invoke_rest_api": [
                    "Succeeded"
                  ]
                }
              },
              "record_rest_api_response": {
                "type": "SetVariable",
                "inputs": {
                  "name": "NativeResponses",
                  "value": "@concat(body('classify_question')?['id'],',',body('invoke_rest_api')?['id'])"
                },
                "runAfter": {
                  "normalize_rest_api": [
                    "Succeeded"
                  ]
                }
              },
              "set_result_rest_api": {
                "type": "SetVariable",
                "inputs": {
                  "name": "Result",
                  "value": "@body('normalize_rest_api')"
                },
                "runAfter": {
                  "record_rest_api_response": [
                    "Succeeded"
                  ]
                }
              }
            }
          },
          "knowledge": {
            "case": "knowledge",
            "actions": {
              "mark_knowledge": {
                "type": "Http",
                "inputs": {
                  "method": "POST",
                  "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
                  "headers": {
                    "Foundry-Features": "WorkflowAgents=V1Preview"
                  },
                  "body": {
                    "items": [
                      {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                          {
                            "type": "output_text",
                            "text": "KPP_ROUTE:knowledge"
                          }
                        ]
                      }
                    ]
                  },
                  "authentication": {
                    "type": "ManagedServiceIdentity",
                    "audience": "https://ai.azure.com"
                  },
                  "retryPolicy": {
                    "type": "none"
                  }
                },
                "runAfter": {}
              },
              "invoke_knowledge": {
                "type": "Http",
                "inputs": {
                  "method": "POST",
                  "uri": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
                  "headers": {
                    "Foundry-Features": "WorkflowAgents=V1Preview"
                  },
                  "body": {
                    "input": "@outputs('capture_question')?['question']",
                    "stream": false,
                    "max_output_tokens": 2048,
                    "conversation": "@body('create_conversation')?['id']",
                    "agent_reference": {
                      "type": "agent_reference",
                      "name": "kppdemo-knowledge",
                      "version": "2"
                    }
                  },
                  "authentication": {
                    "type": "ManagedServiceIdentity",
                    "audience": "https://ai.azure.com"
                  },
                  "retryPolicy": {
                    "type": "none"
                  }
                },
                "runAfter": {
                  "mark_knowledge": [
                    "Succeeded"
                  ]
                }
              },
              "normalize_knowledge": {
                "type": "Http",
                "inputs": {
                  "method": "POST",
                  "uri": "<URL_NORMALIZER>",
                  "headers": {},
                  "body": {
                    "run_id": "@outputs('capture_question')?['run_id']",
                    "route": "knowledge",
                    "response": "@body('invoke_knowledge')"
                  },
                  "authentication": {
                    "type": "ManagedServiceIdentity",
                    "audience": "<AUDIENCE_API>"
                  },
                  "retryPolicy": {
                    "type": "none"
                  }
                },
                "runAfter": {
                  "invoke_knowledge": [
                    "Succeeded"
                  ]
                }
              },
              "record_knowledge_response": {
                "type": "SetVariable",
                "inputs": {
                  "name": "NativeResponses",
                  "value": "@concat(body('classify_question')?['id'],',',body('invoke_knowledge')?['id'])"
                },
                "runAfter": {
                  "normalize_knowledge": [
                    "Succeeded"
                  ]
                }
              },
              "set_result_knowledge": {
                "type": "SetVariable",
                "inputs": {
                  "name": "Result",
                  "value": "@body('normalize_knowledge')"
                },
                "runAfter": {
                  "record_knowledge_response": [
                    "Succeeded"
                  ]
                }
              }
            }
          },
          "foundry_iq": {
            "case": "foundry_iq",
            "actions": {
              "mark_foundry_iq": {
                "type": "Http",
                "inputs": {
                  "method": "POST",
                  "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
                  "headers": {
                    "Foundry-Features": "WorkflowAgents=V1Preview"
                  },
                  "body": {
                    "items": [
                      {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                          {
                            "type": "output_text",
                            "text": "KPP_ROUTE:foundry_iq"
                          }
                        ]
                      }
                    ]
                  },
                  "authentication": {
                    "type": "ManagedServiceIdentity",
                    "audience": "https://ai.azure.com"
                  },
                  "retryPolicy": {
                    "type": "none"
                  }
                },
                "runAfter": {}
              },
              "invoke_foundry_iq": {
                "type": "Http",
                "inputs": {
                  "method": "POST",
                  "uri": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
                  "headers": {
                    "Foundry-Features": "WorkflowAgents=V1Preview"
                  },
                  "body": {
                    "input": "@outputs('capture_question')?['question']",
                    "stream": false,
                    "max_output_tokens": 2048,
                    "conversation": "@body('create_conversation')?['id']",
                    "agent_reference": {
                      "type": "agent_reference",
                      "name": "kppdemo-foundry-iq",
                      "version": "2"
                    }
                  },
                  "authentication": {
                    "type": "ManagedServiceIdentity",
                    "audience": "https://ai.azure.com"
                  },
                  "retryPolicy": {
                    "type": "none"
                  }
                },
                "runAfter": {
                  "mark_foundry_iq": [
                    "Succeeded"
                  ]
                }
              },
              "normalize_foundry_iq": {
                "type": "Http",
                "inputs": {
                  "method": "POST",
                  "uri": "<URL_NORMALIZER>",
                  "headers": {},
                  "body": {
                    "run_id": "@outputs('capture_question')?['run_id']",
                    "route": "foundry_iq",
                    "response": "@body('invoke_foundry_iq')"
                  },
                  "authentication": {
                    "type": "ManagedServiceIdentity",
                    "audience": "<AUDIENCE_API>"
                  },
                  "retryPolicy": {
                    "type": "none"
                  }
                },
                "runAfter": {
                  "invoke_foundry_iq": [
                    "Succeeded"
                  ]
                }
              },
              "record_foundry_iq_response": {
                "type": "SetVariable",
                "inputs": {
                  "name": "NativeResponses",
                  "value": "@concat(body('classify_question')?['id'],',',body('invoke_foundry_iq')?['id'])"
                },
                "runAfter": {
                  "normalize_foundry_iq": [
                    "Succeeded"
                  ]
                }
              },
              "set_result_foundry_iq": {
                "type": "SetVariable",
                "inputs": {
                  "name": "Result",
                  "value": "@body('normalize_foundry_iq')"
                },
                "runAfter": {
                  "record_foundry_iq_response": [
                    "Succeeded"
                  ]
                }
              }
            }
          },
          "fabric_data": {
            "case": "fabric_data",
            "actions": {
              "mark_fabric_data": {
                "type": "Http",
                "inputs": {
                  "method": "POST",
                  "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
                  "headers": {
                    "Foundry-Features": "WorkflowAgents=V1Preview"
                  },
                  "body": {
                    "items": [
                      {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                          {
                            "type": "output_text",
                            "text": "KPP_ROUTE:fabric_data"
                          }
                        ]
                      }
                    ]
                  },
                  "authentication": {
                    "type": "ManagedServiceIdentity",
                    "audience": "https://ai.azure.com"
                  },
                  "retryPolicy": {
                    "type": "none"
                  }
                },
                "runAfter": {}
              },
              "invoke_fabric_data": {
                "type": "Http",
                "inputs": {
                  "method": "POST",
                  "uri": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
                  "headers": {
                    "Foundry-Features": "WorkflowAgents=V1Preview"
                  },
                  "body": {
                    "input": "@outputs('capture_question')?['question']",
                    "stream": false,
                    "max_output_tokens": 2048,
                    "conversation": "@body('create_conversation')?['id']",
                    "agent_reference": {
                      "type": "agent_reference",
                      "name": "kppdemo-fabric-data",
                      "version": "1"
                    }
                  },
                  "authentication": {
                    "type": "ManagedServiceIdentity",
                    "audience": "https://ai.azure.com"
                  },
                  "retryPolicy": {
                    "type": "none"
                  }
                },
                "runAfter": {
                  "mark_fabric_data": [
                    "Succeeded"
                  ]
                }
              },
              "normalize_fabric_data": {
                "type": "Http",
                "inputs": {
                  "method": "POST",
                  "uri": "<URL_NORMALIZER>",
                  "headers": {},
                  "body": {
                    "run_id": "@outputs('capture_question')?['run_id']",
                    "route": "fabric_data",
                    "response": "@body('invoke_fabric_data')"
                  },
                  "authentication": {
                    "type": "ManagedServiceIdentity",
                    "audience": "<AUDIENCE_API>"
                  },
                  "retryPolicy": {
                    "type": "none"
                  }
                },
                "runAfter": {
                  "invoke_fabric_data": [
                    "Succeeded"
                  ]
                }
              },
              "record_fabric_data_response": {
                "type": "SetVariable",
                "inputs": {
                  "name": "NativeResponses",
                  "value": "@concat(body('classify_question')?['id'],',',body('invoke_fabric_data')?['id'])"
                },
                "runAfter": {
                  "normalize_fabric_data": [
                    "Succeeded"
                  ]
                }
              },
              "set_result_fabric_data": {
                "type": "SetVariable",
                "inputs": {
                  "name": "Result",
                  "value": "@body('normalize_fabric_data')"
                },
                "runAfter": {
                  "record_fabric_data_response": [
                    "Succeeded"
                  ]
                }
              }
            }
          },
          "fabric_iq": {
            "case": "fabric_iq",
            "actions": {
              "blocked_fabric_iq": {
                "type": "Http",
                "inputs": {
                  "method": "POST",
                  "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
                  "headers": {
                    "Foundry-Features": "WorkflowAgents=V1Preview"
                  },
                  "body": {
                    "items": [
                      {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                          {
                            "type": "output_text",
                            "text": "KPP_ROUTE:fabric_iq\nKPP_STATUS:blocked\nNative Fabric ontology is unavailable: FeatureNotAvailable."
                          }
                        ]
                      }
                    ]
                  },
                  "authentication": {
                    "type": "ManagedServiceIdentity",
                    "audience": "https://ai.azure.com"
                  },
                  "retryPolicy": {
                    "type": "none"
                  }
                },
                "runAfter": {}
              },
              "set_result_fabric_iq": {
                "type": "SetVariable",
                "inputs": {
                  "name": "Result",
                  "value": {
                    "run_id": "@outputs('capture_question')?['run_id']",
                    "route": "fabric_iq",
                    "status": "blocked",
                    "answer": null,
                    "sources": [],
                    "error": "Native Fabric ontology is unavailable: FeatureNotAvailable."
                  }
                },
                "runAfter": {
                  "blocked_fabric_iq": [
                    "Succeeded"
                  ]
                }
              }
            }
          },
          "work_iq": {
            "case": "work_iq",
            "actions": {
              "blocked_work_iq": {
                "type": "Http",
                "inputs": {
                  "method": "POST",
                  "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
                  "headers": {
                    "Foundry-Features": "WorkflowAgents=V1Preview"
                  },
                  "body": {
                    "items": [
                      {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                          {
                            "type": "output_text",
                            "text": "KPP_ROUTE:work_iq\nKPP_STATUS:blocked\nA separate Work IQ sandbox has not been supplied. No workplace data was accessed."
                          }
                        ]
                      }
                    ]
                  },
                  "authentication": {
                    "type": "ManagedServiceIdentity",
                    "audience": "https://ai.azure.com"
                  },
                  "retryPolicy": {
                    "type": "none"
                  }
                },
                "runAfter": {}
              },
              "set_result_work_iq": {
                "type": "SetVariable",
                "inputs": {
                  "name": "Result",
                  "value": {
                    "run_id": "@outputs('capture_question')?['run_id']",
                    "route": "work_iq",
                    "status": "blocked",
                    "answer": null,
                    "sources": [],
                    "error": "A separate Work IQ sandbox has not been supplied. No workplace data was accessed."
                  }
                },
                "runAfter": {
                  "blocked_work_iq": [
                    "Succeeded"
                  ]
                }
              }
            }
          },
          "clarification": {
            "case": "clarification",
            "actions": {
              "ask_clarification": {
                "type": "Http",
                "inputs": {
                  "method": "POST",
                  "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
                  "headers": {
                    "Foundry-Features": "WorkflowAgents=V1Preview"
                  },
                  "body": {
                    "items": [
                      {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                          {
                            "type": "output_text",
                            "text": "KPP_ROUTE:clarification\nKPP_STATUS:clarification\nPlease specify one topic: production, maintenance, stock, document lookup, or native knowledge retrieval."
                          }
                        ]
                      }
                    ]
                  },
                  "authentication": {
                    "type": "ManagedServiceIdentity",
                    "audience": "https://ai.azure.com"
                  },
                  "retryPolicy": {
                    "type": "none"
                  }
                },
                "runAfter": {}
              },
              "set_result_clarification": {
                "type": "SetVariable",
                "inputs": {
                  "name": "Result",
                  "value": {
                    "run_id": "@outputs('capture_question')?['run_id']",
                    "route": "clarification",
                    "status": "clarification",
                    "answer": "Please specify one topic: production, maintenance, stock, document lookup, or native knowledge retrieval.",
                    "sources": [],
                    "error": null
                  }
                },
                "runAfter": {
                  "ask_clarification": [
                    "Succeeded"
                  ]
                }
              }
            }
          },
          "unsupported": {
            "case": "unsupported",
            "actions": {
              "reject_unsupported": {
                "type": "Http",
                "inputs": {
                  "method": "POST",
                  "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
                  "headers": {
                    "Foundry-Features": "WorkflowAgents=V1Preview"
                  },
                  "body": {
                    "items": [
                      {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                          {
                            "type": "output_text",
                            "text": "KPP_ROUTE:unsupported\nKPP_STATUS:unsupported\nOnly read-only questions about the new synthetic mining demo are supported. Live systems and writes are not accessed."
                          }
                        ]
                      }
                    ]
                  },
                  "authentication": {
                    "type": "ManagedServiceIdentity",
                    "audience": "https://ai.azure.com"
                  },
                  "retryPolicy": {
                    "type": "none"
                  }
                },
                "runAfter": {}
              },
              "set_result_unsupported": {
                "type": "SetVariable",
                "inputs": {
                  "name": "Result",
                  "value": {
                    "run_id": "@outputs('capture_question')?['run_id']",
                    "route": "unsupported",
                    "status": "unsupported",
                    "answer": "Only read-only questions about the new synthetic mining demo are supported. Live systems and writes are not accessed.",
                    "sources": [],
                    "error": null
                  }
                },
                "runAfter": {
                  "reject_unsupported": [
                    "Succeeded"
                  ]
                }
              }
            }
          }
        },
        "default": {
          "actions": {
            "default_invalid_route": {
              "type": "SetVariable",
              "inputs": {
                "name": "Result",
                "value": {
                  "run_id": "@outputs('capture_question')?['run_id']",
                  "route": "unsupported",
                  "status": "failed",
                  "answer": null,
                  "sources": [],
                  "error": "The router returned an unrecognized route. No specialist was invoked."
                }
              },
              "runAfter": {}
            }
          }
        },
        "runAfter": {
          "Parse_router": [
            "Succeeded"
          ]
        }
      },
      "why": "Pertanyaan hanya boleh masuk satu cabang, bukan memanggil semua specialist.",
      "scenario": {
        "number": 13,
        "input": "mcp",
        "output": "Case mcp berjalan; case lain tidak berjalan.",
        "input_kind": "json",
        "output_kind": "text",
        "input_label": "Nilai masuk (contoh)",
        "output_label": "Cabang yang berjalan"
      },
      "purpose": "Memilih satu cabang sesuai nilai route."
    },
    {
      "id": "mark_mcp",
      "title": "mark mcp",
      "type": "Http",
      "group": "Alur contoh TRK001",
      "url": "<ENDPOINT_FOUNDRY>/openai/v1/conversations/{conversation_id}/items",
      "url_note": "conversation_id berasal dari create_conversation.id.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "https://ai.azure.com"
        },
        {
          "name": "Foundry-Features",
          "value": "WorkflowAgents=V1Preview"
        }
      ],
      "input": {
        "items": [
          {
            "type": "message",
            "role": "assistant",
            "content": [
              {
                "type": "output_text",
                "text": "KPP_ROUTE:mcp"
              }
            ]
          }
        ]
      },
      "output": "Activity tersimpan di conversation. Bukan panggilan specialist.",
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
          "headers": {
            "Foundry-Features": "WorkflowAgents=V1Preview"
          },
          "body": {
            "items": [
              {
                "type": "message",
                "role": "assistant",
                "content": [
                  {
                    "type": "output_text",
                    "text": "KPP_ROUTE:mcp"
                  }
                ]
              }
            ]
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "https://ai.azure.com"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {}
      },
      "why": "Penanda ini mencatat cabang/status di riwayat conversation; belum menjalankan tool atau specialist.",
      "scenario": {
        "number": 14,
        "input": {
          "items": [
            {
              "type": "message",
              "role": "assistant",
              "content": [
                {
                  "type": "output_text",
                  "text": "KPP_ROUTE:mcp"
                }
              ]
            }
          ]
        },
        "output": "KPP_ROUTE:mcp tersimpan di conv_contoh. Body respons ini tidak dipakai node berikutnya.",
        "input_kind": "json",
        "output_kind": "text",
        "input_label": "Body dikirim (contoh)",
        "output_label": "Hasil langkah; bukan JSON respons"
      },
      "purpose": "Menulis penanda route/status atau pesan ke conversation."
    },
    {
      "id": "invoke_mcp",
      "title": "invoke mcp",
      "type": "Http",
      "group": "Alur contoh TRK001",
      "url": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
      "url_note": "API project Foundry, bukan URL satu agent. Agent dipilih lewat agent_reference.name dan version pada body.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "https://ai.azure.com"
        },
        {
          "name": "Foundry-Features",
          "value": "WorkflowAgents=V1Preview"
        },
        {
          "name": "Agent",
          "value": "kppdemo-mcp:1"
        }
      ],
      "input": {
        "input": "@outputs('capture_question')?['question']",
        "stream": false,
        "max_output_tokens": 2048,
        "conversation": "@body('create_conversation')?['id']",
        "agent_reference": {
          "type": "agent_reference",
          "name": "kppdemo-mcp",
          "version": "1"
        }
      },
      "output": "Object respons Foundry: id, status dan output[]. Berisi jawaban serta bukti tool.",
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
          "headers": {
            "Foundry-Features": "WorkflowAgents=V1Preview"
          },
          "body": {
            "input": "@outputs('capture_question')?['question']",
            "stream": false,
            "max_output_tokens": 2048,
            "conversation": "@body('create_conversation')?['id']",
            "agent_reference": {
              "type": "agent_reference",
              "name": "kppdemo-mcp",
              "version": "1"
            }
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "https://ai.azure.com"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {
          "mark_mcp": [
            "Succeeded"
          ]
        }
      },
      "why": "Router hanya memilih tujuan. Specialist inilah yang benar-benar meminta data lewat tool.",
      "scenario": {
        "number": 15,
        "input": {
          "input": "Show work orders for equipment TRK001.",
          "stream": false,
          "max_output_tokens": 2048,
          "conversation": "conv_contoh",
          "agent_reference": {
            "type": "agent_reference",
            "name": "kppdemo-mcp",
            "version": "1"
          }
        },
        "output": {
          "id": "resp_mcp_contoh",
          "status": "completed",
          "output": [
            {
              "type": "mcp_call",
              "name": "get_work_orders",
              "status": "completed",
              "agent_reference": {
                "type": "agent_reference",
                "name": "kppdemo-mcp",
                "version": "1"
              },
              "arguments": "{\"equipment_id\":\"TRK001\"}",
              "output": "{\"demo_id\": \"48254cc6\", \"synthetic\": true, \"data\": [{\"order_id\": \"WO001\", \"equipment_id\": \"TRK001\", \"priority\": \"demo-high\", \"status\": \"open\"}], \"sources\": [{\"kind\": \"demo_fixture\", \"id\": \"urn:kppdemo:maintenance/TRK001\"}]}"
            },
            {
              "type": "message",
              "agent_reference": {
                "type": "agent_reference",
                "name": "kppdemo-mcp",
                "version": "1"
              },
              "content": [
                {
                  "type": "output_text",
                  "text": "Work order WO001 for equipment TRK001 is open, with priority demo-high."
                }
              ]
            }
          ]
        },
        "input_kind": "json",
        "output_kind": "json",
        "input_label": "Body dikirim (contoh)",
        "output_label": "Output (contoh)"
      },
      "purpose": "Memanggil specialist untuk membaca data lewat tool."
    },
    {
      "id": "normalize_mcp",
      "title": "normalize mcp",
      "type": "Http",
      "group": "Alur contoh TRK001",
      "url": "<URL_NORMALIZER>",
      "url_note": "API normalizer di App Service, bukan endpoint agent Foundry.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "<AUDIENCE_API>"
        }
      ],
      "input": {
        "run_id": "@outputs('capture_question')?['run_id']",
        "route": "mcp",
        "response": "@body('invoke_mcp')"
      },
      "output": {
        "run_id": "<ID_SANDBOX>",
        "route": "mcp",
        "status": "success",
        "answer": "Found 1 synthetic work order for equipment TRK001 (from demo fixture).\n\nWork order:\n- order_id: WO001\n- equipment_id: TRK001\n- priority: demo-high\n- status: open\n\nSource: urn:kppdemo:maintenance/TRK001",
        "sources": [
          {
            "id": "urn:kppdemo:maintenance/TRK001",
            "kind": "demo_fixture"
          }
        ],
        "error": null
      },
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "<URL_NORMALIZER>",
          "headers": {},
          "body": {
            "run_id": "@outputs('capture_question')?['run_id']",
            "route": "mcp",
            "response": "@body('invoke_mcp')"
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "<AUDIENCE_API>"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {
          "invoke_mcp": [
            "Succeeded"
          ]
        }
      },
      "why": "Jawaban agent harus didukung bukti tool dan sources sebelum ditampilkan sebagai hasil sukses.",
      "scenario": {
        "number": 16,
        "input": {
          "run_id": "<ID_SANDBOX>",
          "route": "mcp",
          "response": {
            "id": "resp_mcp_contoh",
            "status": "completed",
            "output": [
              {
                "type": "mcp_call",
                "name": "get_work_orders",
                "status": "completed",
                "agent_reference": {
                  "type": "agent_reference",
                  "name": "kppdemo-mcp",
                  "version": "1"
                },
                "arguments": "{\"equipment_id\":\"TRK001\"}",
                "output": "{\"demo_id\": \"48254cc6\", \"synthetic\": true, \"data\": [{\"order_id\": \"WO001\", \"equipment_id\": \"TRK001\", \"priority\": \"demo-high\", \"status\": \"open\"}], \"sources\": [{\"kind\": \"demo_fixture\", \"id\": \"urn:kppdemo:maintenance/TRK001\"}]}"
              },
              {
                "type": "message",
                "agent_reference": {
                  "type": "agent_reference",
                  "name": "kppdemo-mcp",
                  "version": "1"
                },
                "content": [
                  {
                    "type": "output_text",
                    "text": "Work order WO001 for equipment TRK001 is open, with priority demo-high."
                  }
                ]
              }
            ]
          }
        },
        "output": {
          "run_id": "<ID_SANDBOX>",
          "route": "mcp",
          "status": "success",
          "answer": "Work order WO001 for equipment TRK001 is open, with priority demo-high.",
          "sources": [
            {
              "kind": "demo_fixture",
              "id": "urn:kppdemo:maintenance/TRK001"
            }
          ],
          "error": null
        },
        "input_kind": "json",
        "output_kind": "json",
        "input_label": "Body dikirim (contoh)",
        "output_label": "Output (contoh)"
      },
      "purpose": "Memeriksa bukti tool dan membentuk hasil yang siap dikirim ke UI."
    },
    {
      "id": "record_mcp_response",
      "title": "record mcp response",
      "type": "SetVariable",
      "group": "Alur contoh TRK001",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Name",
          "value": "NativeResponses"
        },
        {
          "name": "Value",
          "value": "@concat(body('classify_question')?['id'],',',body('invoke_mcp')?['id'])"
        }
      ],
      "input": "ID respons dari classify_question, invoke_mcp.",
      "output": "resp_contoh,resp_contoh",
      "raw": {
        "type": "SetVariable",
        "inputs": {
          "name": "NativeResponses",
          "value": "@concat(body('classify_question')?['id'],',',body('invoke_mcp')?['id'])"
        },
        "runAfter": {
          "normalize_mcp": [
            "Succeeded"
          ]
        }
      },
      "why": "ID respons disimpan supaya hasil UI bisa ditelusuri ke respons router dan specialist di Foundry.",
      "scenario": {
        "number": 17,
        "input": "resp_contoh,resp_mcp_contoh",
        "output": {
          "NativeResponses": "resp_contoh,resp_mcp_contoh"
        },
        "input_kind": "json",
        "output_kind": "json",
        "input_label": "Nilai yang dibaca (contoh)",
        "output_label": "Variabel sesudah (contoh)"
      },
      "purpose": "Mencatat ID respons agent ke NativeResponses."
    },
    {
      "id": "set_result_mcp",
      "title": "set result mcp",
      "type": "SetVariable",
      "group": "Alur contoh TRK001",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Name",
          "value": "Result"
        },
        {
          "name": "Value",
          "value": "@body('normalize_mcp')"
        }
      ],
      "input": "@body('normalize_mcp')",
      "output": {
        "run_id": "<ID_SANDBOX>",
        "route": "mcp",
        "status": "success",
        "answer": "Found 1 synthetic work order for equipment TRK001 (from demo fixture).\n\nWork order:\n- order_id: WO001\n- equipment_id: TRK001\n- priority: demo-high\n- status: open\n\nSource: urn:kppdemo:maintenance/TRK001",
        "sources": [
          {
            "id": "urn:kppdemo:maintenance/TRK001",
            "kind": "demo_fixture"
          }
        ],
        "error": null
      },
      "raw": {
        "type": "SetVariable",
        "inputs": {
          "name": "Result",
          "value": "@body('normalize_mcp')"
        },
        "runAfter": {
          "record_mcp_response": [
            "Succeeded"
          ]
        }
      },
      "why": "Response akhir membaca variabel yang disimpan, bukan otomatis mengambil output action terakhir.",
      "scenario": {
        "number": 18,
        "input": {
          "run_id": "<ID_SANDBOX>",
          "route": "mcp",
          "status": "success",
          "answer": "Work order WO001 for equipment TRK001 is open, with priority demo-high.",
          "sources": [
            {
              "kind": "demo_fixture",
              "id": "urn:kppdemo:maintenance/TRK001"
            }
          ],
          "error": null
        },
        "output": {
          "Result": {
            "run_id": "<ID_SANDBOX>",
            "route": "mcp",
            "status": "success",
            "answer": "Work order WO001 for equipment TRK001 is open, with priority demo-high.",
            "sources": [
              {
                "kind": "demo_fixture",
                "id": "urn:kppdemo:maintenance/TRK001"
              }
            ],
            "error": null
          }
        },
        "input_kind": "json",
        "output_kind": "json",
        "input_label": "Nilai yang dibaca (contoh)",
        "output_label": "Variabel sesudah (contoh)"
      },
      "purpose": "Menyimpan Body normalizer sebagai Result."
    },
    {
      "id": "kpp_mining_end",
      "title": "kpp mining end",
      "type": "Response",
      "group": "Alur contoh TRK001",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Status Code",
          "value": "200; 502 jika Result.status = failed"
        },
        {
          "name": "Content-Type",
          "value": "application/json"
        }
      ],
      "input": "@variables('Result')",
      "output": {
        "run_id": "<ID_SANDBOX>",
        "route": "mcp",
        "status": "success",
        "answer": "Found 1 synthetic work order for equipment TRK001 (from demo fixture).\n\nWork order:\n- order_id: WO001\n- equipment_id: TRK001\n- priority: demo-high\n- status: open\n\nSource: urn:kppdemo:maintenance/TRK001",
        "sources": [
          {
            "id": "urn:kppdemo:maintenance/TRK001",
            "kind": "demo_fixture"
          }
        ],
        "error": null
      },
      "raw": {
        "type": "Response",
        "kind": "Http",
        "runAfter": {
          "Execute": [
            "Succeeded",
            "Failed",
            "TimedOut"
          ]
        },
        "inputs": {
          "statusCode": "@if(equals(variables('Result')?['status'],'failed'),502,200)",
          "body": "@variables('Result')",
          "headers": {
            "Content-Type": "application/json",
            "x-kpp-orchestrator": "logic_apps",
            "x-kpp-source-sha256": "8a1b3b54903f26864bf81fad662e847cc97df18a945f536db9ff78b90aa4a8e1",
            "x-kpp-logic-run": "@workflow()['run']['name']",
            "x-kpp-native-responses": "@variables('NativeResponses')",
            "x-kpp-route": "@variables('Result')?['route']"
          }
        }
      },
      "why": "Pemanggil HTTP perlu menerima hasil akhir atau kesalahan dari workflow.",
      "scenario": {
        "number": 19,
        "input": {
          "run_id": "<ID_SANDBOX>",
          "route": "mcp",
          "status": "success",
          "answer": "Work order WO001 for equipment TRK001 is open, with priority demo-high.",
          "sources": [
            {
              "kind": "demo_fixture",
              "id": "urn:kppdemo:maintenance/TRK001"
            }
          ],
          "error": null
        },
        "output": {
          "statusCode": 200,
          "headers": {
            "Content-Type": "application/json",
            "x-kpp-orchestrator": "logic_apps",
            "x-kpp-logic-run": "085...CONTOH",
            "x-kpp-native-responses": "resp_contoh,resp_mcp_contoh",
            "x-kpp-route": "mcp"
          },
          "body": {
            "run_id": "<ID_SANDBOX>",
            "route": "mcp",
            "status": "success",
            "answer": "Work order WO001 for equipment TRK001 is open, with priority demo-high.",
            "sources": [
              {
                "kind": "demo_fixture",
                "id": "urn:kppdemo:maintenance/TRK001"
              }
            ],
            "error": null
          }
        },
        "input_kind": "json",
        "output_kind": "json",
        "input_label": "Nilai masuk (contoh)",
        "output_label": "HTTP balasan (contoh)"
      },
      "purpose": "Mengirim Result kembali ke pemanggil/UI."
    },
    {
      "id": "mark_rest_api",
      "title": "mark rest api",
      "type": "Http",
      "group": "Stok REST API",
      "url": "<ENDPOINT_FOUNDRY>/openai/v1/conversations/{conversation_id}/items",
      "url_note": "conversation_id berasal dari create_conversation.id.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "https://ai.azure.com"
        },
        {
          "name": "Foundry-Features",
          "value": "WorkflowAgents=V1Preview"
        }
      ],
      "input": {
        "items": [
          {
            "type": "message",
            "role": "assistant",
            "content": [
              {
                "type": "output_text",
                "text": "KPP_ROUTE:rest_api"
              }
            ]
          }
        ]
      },
      "output": "Activity tersimpan di conversation. Bukan panggilan specialist.",
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
          "headers": {
            "Foundry-Features": "WorkflowAgents=V1Preview"
          },
          "body": {
            "items": [
              {
                "type": "message",
                "role": "assistant",
                "content": [
                  {
                    "type": "output_text",
                    "text": "KPP_ROUTE:rest_api"
                  }
                ]
              }
            ]
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "https://ai.azure.com"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {}
      },
      "why": "Penanda ini mencatat cabang/status di riwayat conversation; belum menjalankan tool atau specialist.",
      "scenario": null,
      "purpose": "Menulis penanda route/status atau pesan ke conversation."
    },
    {
      "id": "invoke_rest_api",
      "title": "invoke rest api",
      "type": "Http",
      "group": "Stok REST API",
      "url": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
      "url_note": "API project Foundry, bukan URL satu agent. Agent dipilih lewat agent_reference.name dan version pada body.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "https://ai.azure.com"
        },
        {
          "name": "Foundry-Features",
          "value": "WorkflowAgents=V1Preview"
        },
        {
          "name": "Agent",
          "value": "kppdemo-rest:4"
        }
      ],
      "input": {
        "input": "@outputs('capture_question')?['question']",
        "stream": false,
        "max_output_tokens": 2048,
        "conversation": "@body('create_conversation')?['id']",
        "agent_reference": {
          "type": "agent_reference",
          "name": "kppdemo-rest",
          "version": "4"
        }
      },
      "output": "Object respons Foundry: id, status dan output[]. Berisi jawaban serta bukti tool.",
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
          "headers": {
            "Foundry-Features": "WorkflowAgents=V1Preview"
          },
          "body": {
            "input": "@outputs('capture_question')?['question']",
            "stream": false,
            "max_output_tokens": 2048,
            "conversation": "@body('create_conversation')?['id']",
            "agent_reference": {
              "type": "agent_reference",
              "name": "kppdemo-rest",
              "version": "4"
            }
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "https://ai.azure.com"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {
          "mark_rest_api": [
            "Succeeded"
          ]
        }
      },
      "why": "Router hanya memilih tujuan. Specialist inilah yang benar-benar meminta data lewat tool.",
      "scenario": null,
      "purpose": "Memanggil specialist untuk membaca data lewat tool."
    },
    {
      "id": "normalize_rest_api",
      "title": "normalize rest api",
      "type": "Http",
      "group": "Stok REST API",
      "url": "<URL_NORMALIZER>",
      "url_note": "API normalizer di App Service, bukan endpoint agent Foundry.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "<AUDIENCE_API>"
        }
      ],
      "input": {
        "run_id": "@outputs('capture_question')?['run_id']",
        "route": "rest_api",
        "response": "@body('invoke_rest_api')"
      },
      "output": {
        "run_id": "<ID_SANDBOX>",
        "route": "rest_api",
        "status": "success",
        "answer": "There are 18,000 litres of DIESEL at MS01.\n\nRecord ID: urn:kppdemo:stock/MS01/DIESEL\nSource: https (upstream_protocol: https_rest, outbound_auth: managed_identity)",
        "sources": [
          {
            "id": "urn:kppdemo:stock/MS01/DIESEL",
            "kind": "demo_fixture"
          }
        ],
        "error": null
      },
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "<URL_NORMALIZER>",
          "headers": {},
          "body": {
            "run_id": "@outputs('capture_question')?['run_id']",
            "route": "rest_api",
            "response": "@body('invoke_rest_api')"
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "<AUDIENCE_API>"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {
          "invoke_rest_api": [
            "Succeeded"
          ]
        }
      },
      "why": "Jawaban agent harus didukung bukti tool dan sources sebelum ditampilkan sebagai hasil sukses.",
      "scenario": null,
      "purpose": "Memeriksa bukti tool dan membentuk hasil yang siap dikirim ke UI."
    },
    {
      "id": "record_rest_api_response",
      "title": "record rest api response",
      "type": "SetVariable",
      "group": "Stok REST API",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Name",
          "value": "NativeResponses"
        },
        {
          "name": "Value",
          "value": "@concat(body('classify_question')?['id'],',',body('invoke_rest_api')?['id'])"
        }
      ],
      "input": "ID respons dari classify_question, invoke_rest_api.",
      "output": "resp_contoh,resp_contoh",
      "raw": {
        "type": "SetVariable",
        "inputs": {
          "name": "NativeResponses",
          "value": "@concat(body('classify_question')?['id'],',',body('invoke_rest_api')?['id'])"
        },
        "runAfter": {
          "normalize_rest_api": [
            "Succeeded"
          ]
        }
      },
      "why": "ID respons disimpan supaya hasil UI bisa ditelusuri ke respons router dan specialist di Foundry.",
      "scenario": null,
      "purpose": "Mencatat ID respons agent ke NativeResponses."
    },
    {
      "id": "set_result_rest_api",
      "title": "set result rest api",
      "type": "SetVariable",
      "group": "Stok REST API",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Name",
          "value": "Result"
        },
        {
          "name": "Value",
          "value": "@body('normalize_rest_api')"
        }
      ],
      "input": "@body('normalize_rest_api')",
      "output": {
        "run_id": "<ID_SANDBOX>",
        "route": "rest_api",
        "status": "success",
        "answer": "There are 18,000 litres of DIESEL at MS01.\n\nRecord ID: urn:kppdemo:stock/MS01/DIESEL\nSource: https (upstream_protocol: https_rest, outbound_auth: managed_identity)",
        "sources": [
          {
            "id": "urn:kppdemo:stock/MS01/DIESEL",
            "kind": "demo_fixture"
          }
        ],
        "error": null
      },
      "raw": {
        "type": "SetVariable",
        "inputs": {
          "name": "Result",
          "value": "@body('normalize_rest_api')"
        },
        "runAfter": {
          "record_rest_api_response": [
            "Succeeded"
          ]
        }
      },
      "why": "Response akhir membaca variabel yang disimpan, bukan otomatis mengambil output action terakhir.",
      "scenario": null,
      "purpose": "Menyimpan Body normalizer sebagai Result."
    },
    {
      "id": "mark_knowledge",
      "title": "mark knowledge",
      "type": "Http",
      "group": "Dokumen Search",
      "url": "<ENDPOINT_FOUNDRY>/openai/v1/conversations/{conversation_id}/items",
      "url_note": "conversation_id berasal dari create_conversation.id.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "https://ai.azure.com"
        },
        {
          "name": "Foundry-Features",
          "value": "WorkflowAgents=V1Preview"
        }
      ],
      "input": {
        "items": [
          {
            "type": "message",
            "role": "assistant",
            "content": [
              {
                "type": "output_text",
                "text": "KPP_ROUTE:knowledge"
              }
            ]
          }
        ]
      },
      "output": "Activity tersimpan di conversation. Bukan panggilan specialist.",
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
          "headers": {
            "Foundry-Features": "WorkflowAgents=V1Preview"
          },
          "body": {
            "items": [
              {
                "type": "message",
                "role": "assistant",
                "content": [
                  {
                    "type": "output_text",
                    "text": "KPP_ROUTE:knowledge"
                  }
                ]
              }
            ]
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "https://ai.azure.com"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {}
      },
      "why": "Penanda ini mencatat cabang/status di riwayat conversation; belum menjalankan tool atau specialist.",
      "scenario": null,
      "purpose": "Menulis penanda route/status atau pesan ke conversation."
    },
    {
      "id": "invoke_knowledge",
      "title": "invoke knowledge",
      "type": "Http",
      "group": "Dokumen Search",
      "url": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
      "url_note": "API project Foundry, bukan URL satu agent. Agent dipilih lewat agent_reference.name dan version pada body.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "https://ai.azure.com"
        },
        {
          "name": "Foundry-Features",
          "value": "WorkflowAgents=V1Preview"
        },
        {
          "name": "Agent",
          "value": "kppdemo-knowledge:2"
        }
      ],
      "input": {
        "input": "@outputs('capture_question')?['question']",
        "stream": false,
        "max_output_tokens": 2048,
        "conversation": "@body('create_conversation')?['id']",
        "agent_reference": {
          "type": "agent_reference",
          "name": "kppdemo-knowledge",
          "version": "2"
        }
      },
      "output": "Object respons Foundry: id, status dan output[]. Berisi jawaban serta bukti tool.",
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
          "headers": {
            "Foundry-Features": "WorkflowAgents=V1Preview"
          },
          "body": {
            "input": "@outputs('capture_question')?['question']",
            "stream": false,
            "max_output_tokens": 2048,
            "conversation": "@body('create_conversation')?['id']",
            "agent_reference": {
              "type": "agent_reference",
              "name": "kppdemo-knowledge",
              "version": "2"
            }
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "https://ai.azure.com"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {
          "mark_knowledge": [
            "Succeeded"
          ]
        }
      },
      "why": "Router hanya memilih tujuan. Specialist inilah yang benar-benar meminta data lewat tool.",
      "scenario": null,
      "purpose": "Memanggil specialist untuk membaca data lewat tool."
    },
    {
      "id": "normalize_knowledge",
      "title": "normalize knowledge",
      "type": "Http",
      "group": "Dokumen Search",
      "url": "<URL_NORMALIZER>",
      "url_note": "API normalizer di App Service, bukan endpoint agent Foundry.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "<AUDIENCE_API>"
        }
      ],
      "input": {
        "run_id": "@outputs('capture_question')?['run_id']",
        "route": "knowledge",
        "response": "@body('invoke_knowledge')"
      },
      "output": {
        "run_id": "<ID_SANDBOX>",
        "route": "knowledge",
        "status": "success",
        "answer": "Found one relevant synthetic document.\n\n- Document ID: DMO-DOC-01\n- Title: Synthetic Copper Ridge reporting code\n- Reporting code (from document): DEMO-COPPER-17\n- Source URI: urn:kppdemo:knowledge/DMO-DOC-01\n\nNote: All results are fictional demo data.",
        "sources": [
          {
            "id": "urn:kppdemo:knowledge/DMO-DOC-01",
            "kind": "demo_document"
          },
          {
            "id": "urn:kppdemo:knowledge/DMO-DOC-02",
            "kind": "demo_document"
          },
          {
            "id": "urn:kppdemo:knowledge/DMO-DOC-03",
            "kind": "demo_document"
          }
        ],
        "error": null
      },
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "<URL_NORMALIZER>",
          "headers": {},
          "body": {
            "run_id": "@outputs('capture_question')?['run_id']",
            "route": "knowledge",
            "response": "@body('invoke_knowledge')"
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "<AUDIENCE_API>"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {
          "invoke_knowledge": [
            "Succeeded"
          ]
        }
      },
      "why": "Jawaban agent harus didukung bukti tool dan sources sebelum ditampilkan sebagai hasil sukses.",
      "scenario": null,
      "purpose": "Memeriksa bukti tool dan membentuk hasil yang siap dikirim ke UI."
    },
    {
      "id": "record_knowledge_response",
      "title": "record knowledge response",
      "type": "SetVariable",
      "group": "Dokumen Search",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Name",
          "value": "NativeResponses"
        },
        {
          "name": "Value",
          "value": "@concat(body('classify_question')?['id'],',',body('invoke_knowledge')?['id'])"
        }
      ],
      "input": "ID respons dari classify_question, invoke_knowledge.",
      "output": "resp_contoh,resp_contoh",
      "raw": {
        "type": "SetVariable",
        "inputs": {
          "name": "NativeResponses",
          "value": "@concat(body('classify_question')?['id'],',',body('invoke_knowledge')?['id'])"
        },
        "runAfter": {
          "normalize_knowledge": [
            "Succeeded"
          ]
        }
      },
      "why": "ID respons disimpan supaya hasil UI bisa ditelusuri ke respons router dan specialist di Foundry.",
      "scenario": null,
      "purpose": "Mencatat ID respons agent ke NativeResponses."
    },
    {
      "id": "set_result_knowledge",
      "title": "set result knowledge",
      "type": "SetVariable",
      "group": "Dokumen Search",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Name",
          "value": "Result"
        },
        {
          "name": "Value",
          "value": "@body('normalize_knowledge')"
        }
      ],
      "input": "@body('normalize_knowledge')",
      "output": {
        "run_id": "<ID_SANDBOX>",
        "route": "knowledge",
        "status": "success",
        "answer": "Found one relevant synthetic document.\n\n- Document ID: DMO-DOC-01\n- Title: Synthetic Copper Ridge reporting code\n- Reporting code (from document): DEMO-COPPER-17\n- Source URI: urn:kppdemo:knowledge/DMO-DOC-01\n\nNote: All results are fictional demo data.",
        "sources": [
          {
            "id": "urn:kppdemo:knowledge/DMO-DOC-01",
            "kind": "demo_document"
          },
          {
            "id": "urn:kppdemo:knowledge/DMO-DOC-02",
            "kind": "demo_document"
          },
          {
            "id": "urn:kppdemo:knowledge/DMO-DOC-03",
            "kind": "demo_document"
          }
        ],
        "error": null
      },
      "raw": {
        "type": "SetVariable",
        "inputs": {
          "name": "Result",
          "value": "@body('normalize_knowledge')"
        },
        "runAfter": {
          "record_knowledge_response": [
            "Succeeded"
          ]
        }
      },
      "why": "Response akhir membaca variabel yang disimpan, bukan otomatis mengambil output action terakhir.",
      "scenario": null,
      "purpose": "Menyimpan Body normalizer sebagai Result."
    },
    {
      "id": "mark_foundry_iq",
      "title": "mark foundry iq",
      "type": "Http",
      "group": "Native knowledge base",
      "url": "<ENDPOINT_FOUNDRY>/openai/v1/conversations/{conversation_id}/items",
      "url_note": "conversation_id berasal dari create_conversation.id.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "https://ai.azure.com"
        },
        {
          "name": "Foundry-Features",
          "value": "WorkflowAgents=V1Preview"
        }
      ],
      "input": {
        "items": [
          {
            "type": "message",
            "role": "assistant",
            "content": [
              {
                "type": "output_text",
                "text": "KPP_ROUTE:foundry_iq"
              }
            ]
          }
        ]
      },
      "output": "Activity tersimpan di conversation. Bukan panggilan specialist.",
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
          "headers": {
            "Foundry-Features": "WorkflowAgents=V1Preview"
          },
          "body": {
            "items": [
              {
                "type": "message",
                "role": "assistant",
                "content": [
                  {
                    "type": "output_text",
                    "text": "KPP_ROUTE:foundry_iq"
                  }
                ]
              }
            ]
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "https://ai.azure.com"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {}
      },
      "why": "Penanda ini mencatat cabang/status di riwayat conversation; belum menjalankan tool atau specialist.",
      "scenario": null,
      "purpose": "Menulis penanda route/status atau pesan ke conversation."
    },
    {
      "id": "invoke_foundry_iq",
      "title": "invoke foundry iq",
      "type": "Http",
      "group": "Native knowledge base",
      "url": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
      "url_note": "API project Foundry, bukan URL satu agent. Agent dipilih lewat agent_reference.name dan version pada body.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "https://ai.azure.com"
        },
        {
          "name": "Foundry-Features",
          "value": "WorkflowAgents=V1Preview"
        },
        {
          "name": "Agent",
          "value": "kppdemo-foundry-iq:2"
        }
      ],
      "input": {
        "input": "@outputs('capture_question')?['question']",
        "stream": false,
        "max_output_tokens": 2048,
        "conversation": "@body('create_conversation')?['id']",
        "agent_reference": {
          "type": "agent_reference",
          "name": "kppdemo-foundry-iq",
          "version": "2"
        }
      },
      "output": "Object respons Foundry: id, status dan output[]. Berisi jawaban serta bukti tool.",
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
          "headers": {
            "Foundry-Features": "WorkflowAgents=V1Preview"
          },
          "body": {
            "input": "@outputs('capture_question')?['question']",
            "stream": false,
            "max_output_tokens": 2048,
            "conversation": "@body('create_conversation')?['id']",
            "agent_reference": {
              "type": "agent_reference",
              "name": "kppdemo-foundry-iq",
              "version": "2"
            }
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "https://ai.azure.com"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {
          "mark_foundry_iq": [
            "Succeeded"
          ]
        }
      },
      "why": "Router hanya memilih tujuan. Specialist inilah yang benar-benar meminta data lewat tool.",
      "scenario": null,
      "purpose": "Memanggil specialist untuk membaca data lewat tool."
    },
    {
      "id": "normalize_foundry_iq",
      "title": "normalize foundry iq",
      "type": "Http",
      "group": "Native knowledge base",
      "url": "<URL_NORMALIZER>",
      "url_note": "API normalizer di App Service, bukan endpoint agent Foundry.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "<AUDIENCE_API>"
        }
      ],
      "input": {
        "run_id": "@outputs('capture_question')?['run_id']",
        "route": "foundry_iq",
        "response": "@body('invoke_foundry_iq')"
      },
      "output": {
        "run_id": "<ID_SANDBOX>",
        "route": "foundry_iq",
        "status": "success",
        "answer": "Result retrieved via Foundry IQ native knowledge-base retrieval (knowledge_base: kppdemo-mining-knowledge). No auth errors.\n\nAnswer (extractive):\n- Copper Ridge (site MS01) reporting code: DEMO-COPPER-17.\n\nSource documents returned:\n- docKey: DMO-DOC-01 \u2014 title: \"Synthetic Copper Ridge reporting code\" \u2014 source_uri: (not provided) \u2014 contains the reporting code text.\n- docKey: DMO-DOC-03 \u2014 title: \"Synthetic equipment-to-site mapping\" \u2014 source_uri: (not provided).\n\nRaw excerpt (from DMO-DOC-01): \"The reporting code for Demo Copper Ridge, site MS01, is DEMO-COPPER-17.\"",
        "sources": [
          {
            "id": "DMO-DOC-01",
            "kind": "knowledge_base_document"
          },
          {
            "id": "DMO-DOC-03",
            "kind": "knowledge_base_document"
          }
        ],
        "error": null
      },
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "<URL_NORMALIZER>",
          "headers": {},
          "body": {
            "run_id": "@outputs('capture_question')?['run_id']",
            "route": "foundry_iq",
            "response": "@body('invoke_foundry_iq')"
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "<AUDIENCE_API>"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {
          "invoke_foundry_iq": [
            "Succeeded"
          ]
        }
      },
      "why": "Jawaban agent harus didukung bukti tool dan sources sebelum ditampilkan sebagai hasil sukses.",
      "scenario": null,
      "purpose": "Memeriksa bukti tool dan membentuk hasil yang siap dikirim ke UI."
    },
    {
      "id": "record_foundry_iq_response",
      "title": "record foundry iq response",
      "type": "SetVariable",
      "group": "Native knowledge base",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Name",
          "value": "NativeResponses"
        },
        {
          "name": "Value",
          "value": "@concat(body('classify_question')?['id'],',',body('invoke_foundry_iq')?['id'])"
        }
      ],
      "input": "ID respons dari classify_question, invoke_foundry_iq.",
      "output": "resp_contoh,resp_contoh",
      "raw": {
        "type": "SetVariable",
        "inputs": {
          "name": "NativeResponses",
          "value": "@concat(body('classify_question')?['id'],',',body('invoke_foundry_iq')?['id'])"
        },
        "runAfter": {
          "normalize_foundry_iq": [
            "Succeeded"
          ]
        }
      },
      "why": "ID respons disimpan supaya hasil UI bisa ditelusuri ke respons router dan specialist di Foundry.",
      "scenario": null,
      "purpose": "Mencatat ID respons agent ke NativeResponses."
    },
    {
      "id": "set_result_foundry_iq",
      "title": "set result foundry iq",
      "type": "SetVariable",
      "group": "Native knowledge base",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Name",
          "value": "Result"
        },
        {
          "name": "Value",
          "value": "@body('normalize_foundry_iq')"
        }
      ],
      "input": "@body('normalize_foundry_iq')",
      "output": {
        "run_id": "<ID_SANDBOX>",
        "route": "foundry_iq",
        "status": "success",
        "answer": "Result retrieved via Foundry IQ native knowledge-base retrieval (knowledge_base: kppdemo-mining-knowledge). No auth errors.\n\nAnswer (extractive):\n- Copper Ridge (site MS01) reporting code: DEMO-COPPER-17.\n\nSource documents returned:\n- docKey: DMO-DOC-01 \u2014 title: \"Synthetic Copper Ridge reporting code\" \u2014 source_uri: (not provided) \u2014 contains the reporting code text.\n- docKey: DMO-DOC-03 \u2014 title: \"Synthetic equipment-to-site mapping\" \u2014 source_uri: (not provided).\n\nRaw excerpt (from DMO-DOC-01): \"The reporting code for Demo Copper Ridge, site MS01, is DEMO-COPPER-17.\"",
        "sources": [
          {
            "id": "DMO-DOC-01",
            "kind": "knowledge_base_document"
          },
          {
            "id": "DMO-DOC-03",
            "kind": "knowledge_base_document"
          }
        ],
        "error": null
      },
      "raw": {
        "type": "SetVariable",
        "inputs": {
          "name": "Result",
          "value": "@body('normalize_foundry_iq')"
        },
        "runAfter": {
          "record_foundry_iq_response": [
            "Succeeded"
          ]
        }
      },
      "why": "Response akhir membaca variabel yang disimpan, bukan otomatis mengambil output action terakhir.",
      "scenario": null,
      "purpose": "Menyimpan Body normalizer sebagai Result."
    },
    {
      "id": "mark_fabric_data",
      "title": "mark fabric data",
      "type": "Http",
      "group": "Produksi Fabric",
      "url": "<ENDPOINT_FOUNDRY>/openai/v1/conversations/{conversation_id}/items",
      "url_note": "conversation_id berasal dari create_conversation.id.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "https://ai.azure.com"
        },
        {
          "name": "Foundry-Features",
          "value": "WorkflowAgents=V1Preview"
        }
      ],
      "input": {
        "items": [
          {
            "type": "message",
            "role": "assistant",
            "content": [
              {
                "type": "output_text",
                "text": "KPP_ROUTE:fabric_data"
              }
            ]
          }
        ]
      },
      "output": "Activity tersimpan di conversation. Bukan panggilan specialist.",
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
          "headers": {
            "Foundry-Features": "WorkflowAgents=V1Preview"
          },
          "body": {
            "items": [
              {
                "type": "message",
                "role": "assistant",
                "content": [
                  {
                    "type": "output_text",
                    "text": "KPP_ROUTE:fabric_data"
                  }
                ]
              }
            ]
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "https://ai.azure.com"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {}
      },
      "why": "Penanda ini mencatat cabang/status di riwayat conversation; belum menjalankan tool atau specialist.",
      "scenario": null,
      "purpose": "Menulis penanda route/status atau pesan ke conversation."
    },
    {
      "id": "invoke_fabric_data",
      "title": "invoke fabric data",
      "type": "Http",
      "group": "Produksi Fabric",
      "url": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
      "url_note": "API project Foundry, bukan URL satu agent. Agent dipilih lewat agent_reference.name dan version pada body.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "https://ai.azure.com"
        },
        {
          "name": "Foundry-Features",
          "value": "WorkflowAgents=V1Preview"
        },
        {
          "name": "Agent",
          "value": "kppdemo-fabric-data:1"
        }
      ],
      "input": {
        "input": "@outputs('capture_question')?['question']",
        "stream": false,
        "max_output_tokens": 2048,
        "conversation": "@body('create_conversation')?['id']",
        "agent_reference": {
          "type": "agent_reference",
          "name": "kppdemo-fabric-data",
          "version": "1"
        }
      },
      "output": "Object respons Foundry: id, status dan output[]. Berisi jawaban serta bukti tool.",
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "<ENDPOINT_FOUNDRY>/openai/v1/responses",
          "headers": {
            "Foundry-Features": "WorkflowAgents=V1Preview"
          },
          "body": {
            "input": "@outputs('capture_question')?['question']",
            "stream": false,
            "max_output_tokens": 2048,
            "conversation": "@body('create_conversation')?['id']",
            "agent_reference": {
              "type": "agent_reference",
              "name": "kppdemo-fabric-data",
              "version": "1"
            }
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "https://ai.azure.com"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {
          "mark_fabric_data": [
            "Succeeded"
          ]
        }
      },
      "why": "Router hanya memilih tujuan. Specialist inilah yang benar-benar meminta data lewat tool.",
      "scenario": null,
      "purpose": "Memanggil specialist untuk membaca data lewat tool."
    },
    {
      "id": "normalize_fabric_data",
      "title": "normalize fabric data",
      "type": "Http",
      "group": "Produksi Fabric",
      "url": "<URL_NORMALIZER>",
      "url_note": "API normalizer di App Service, bukan endpoint agent Foundry.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "<AUDIENCE_API>"
        }
      ],
      "input": {
        "run_id": "@outputs('capture_question')?['run_id']",
        "route": "fabric_data",
        "response": "@body('invoke_fabric_data')"
      },
      "output": {
        "run_id": "<ID_SANDBOX>",
        "route": "fabric_data",
        "status": "success",
        "answer": "Production for site MS01 on 2026-11-01 (day shift): 1250 tonnes.",
        "sources": [
          {
            "id": "kpp_mining_data_us_48254cc6",
            "kind": "fabric_data_agent"
          }
        ],
        "error": null
      },
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "<URL_NORMALIZER>",
          "headers": {},
          "body": {
            "run_id": "@outputs('capture_question')?['run_id']",
            "route": "fabric_data",
            "response": "@body('invoke_fabric_data')"
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "<AUDIENCE_API>"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {
          "invoke_fabric_data": [
            "Succeeded"
          ]
        }
      },
      "why": "Jawaban agent harus didukung bukti tool dan sources sebelum ditampilkan sebagai hasil sukses.",
      "scenario": null,
      "purpose": "Memeriksa bukti tool dan membentuk hasil yang siap dikirim ke UI."
    },
    {
      "id": "record_fabric_data_response",
      "title": "record fabric data response",
      "type": "SetVariable",
      "group": "Produksi Fabric",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Name",
          "value": "NativeResponses"
        },
        {
          "name": "Value",
          "value": "@concat(body('classify_question')?['id'],',',body('invoke_fabric_data')?['id'])"
        }
      ],
      "input": "ID respons dari classify_question, invoke_fabric_data.",
      "output": "resp_contoh,resp_contoh",
      "raw": {
        "type": "SetVariable",
        "inputs": {
          "name": "NativeResponses",
          "value": "@concat(body('classify_question')?['id'],',',body('invoke_fabric_data')?['id'])"
        },
        "runAfter": {
          "normalize_fabric_data": [
            "Succeeded"
          ]
        }
      },
      "why": "ID respons disimpan supaya hasil UI bisa ditelusuri ke respons router dan specialist di Foundry.",
      "scenario": null,
      "purpose": "Mencatat ID respons agent ke NativeResponses."
    },
    {
      "id": "set_result_fabric_data",
      "title": "set result fabric data",
      "type": "SetVariable",
      "group": "Produksi Fabric",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Name",
          "value": "Result"
        },
        {
          "name": "Value",
          "value": "@body('normalize_fabric_data')"
        }
      ],
      "input": "@body('normalize_fabric_data')",
      "output": {
        "run_id": "<ID_SANDBOX>",
        "route": "fabric_data",
        "status": "success",
        "answer": "Production for site MS01 on 2026-11-01 (day shift): 1250 tonnes.",
        "sources": [
          {
            "id": "kpp_mining_data_us_48254cc6",
            "kind": "fabric_data_agent"
          }
        ],
        "error": null
      },
      "raw": {
        "type": "SetVariable",
        "inputs": {
          "name": "Result",
          "value": "@body('normalize_fabric_data')"
        },
        "runAfter": {
          "record_fabric_data_response": [
            "Succeeded"
          ]
        }
      },
      "why": "Response akhir membaca variabel yang disimpan, bukan otomatis mengambil output action terakhir.",
      "scenario": null,
      "purpose": "Menyimpan Body normalizer sebagai Result."
    },
    {
      "id": "blocked_fabric_iq",
      "title": "blocked fabric iq",
      "type": "Http",
      "group": "Ontology belum tersedia",
      "url": "<ENDPOINT_FOUNDRY>/openai/v1/conversations/{conversation_id}/items",
      "url_note": "conversation_id berasal dari create_conversation.id.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "https://ai.azure.com"
        },
        {
          "name": "Foundry-Features",
          "value": "WorkflowAgents=V1Preview"
        }
      ],
      "input": {
        "items": [
          {
            "type": "message",
            "role": "assistant",
            "content": [
              {
                "type": "output_text",
                "text": "KPP_ROUTE:fabric_iq\nKPP_STATUS:blocked\nNative Fabric ontology is unavailable: FeatureNotAvailable."
              }
            ]
          }
        ]
      },
      "output": "Activity tersimpan di conversation. Bukan panggilan specialist.",
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
          "headers": {
            "Foundry-Features": "WorkflowAgents=V1Preview"
          },
          "body": {
            "items": [
              {
                "type": "message",
                "role": "assistant",
                "content": [
                  {
                    "type": "output_text",
                    "text": "KPP_ROUTE:fabric_iq\nKPP_STATUS:blocked\nNative Fabric ontology is unavailable: FeatureNotAvailable."
                  }
                ]
              }
            ]
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "https://ai.azure.com"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {}
      },
      "why": "Penanda ini mencatat cabang/status di riwayat conversation; belum menjalankan tool atau specialist.",
      "scenario": null,
      "purpose": "Menulis penanda route/status atau pesan ke conversation."
    },
    {
      "id": "set_result_fabric_iq",
      "title": "set result fabric iq",
      "type": "SetVariable",
      "group": "Ontology belum tersedia",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Name",
          "value": "Result"
        },
        {
          "name": "Value",
          "value": {
            "run_id": "@outputs('capture_question')?['run_id']",
            "route": "fabric_iq",
            "status": "blocked",
            "answer": null,
            "sources": [],
            "error": "Native Fabric ontology is unavailable: FeatureNotAvailable."
          }
        }
      ],
      "input": "Object tetap yang disiapkan pada node ini.",
      "output": {
        "run_id": "<ID_SANDBOX>",
        "route": "fabric_iq",
        "status": "blocked",
        "answer": null,
        "sources": [],
        "error": "Native Fabric ontology is unavailable: FeatureNotAvailable."
      },
      "raw": {
        "type": "SetVariable",
        "inputs": {
          "name": "Result",
          "value": {
            "run_id": "@outputs('capture_question')?['run_id']",
            "route": "fabric_iq",
            "status": "blocked",
            "answer": null,
            "sources": [],
            "error": "Native Fabric ontology is unavailable: FeatureNotAvailable."
          }
        },
        "runAfter": {
          "blocked_fabric_iq": [
            "Succeeded"
          ]
        }
      },
      "why": "Response akhir membaca variabel yang disimpan, bukan otomatis mengambil output action terakhir.",
      "scenario": null,
      "purpose": "Mengisi Result dengan status blocked."
    },
    {
      "id": "blocked_work_iq",
      "title": "blocked work iq",
      "type": "Http",
      "group": "Work IQ belum tersedia",
      "url": "<ENDPOINT_FOUNDRY>/openai/v1/conversations/{conversation_id}/items",
      "url_note": "conversation_id berasal dari create_conversation.id.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "https://ai.azure.com"
        },
        {
          "name": "Foundry-Features",
          "value": "WorkflowAgents=V1Preview"
        }
      ],
      "input": {
        "items": [
          {
            "type": "message",
            "role": "assistant",
            "content": [
              {
                "type": "output_text",
                "text": "KPP_ROUTE:work_iq\nKPP_STATUS:blocked\nA separate Work IQ sandbox has not been supplied. No workplace data was accessed."
              }
            ]
          }
        ]
      },
      "output": "Activity tersimpan di conversation. Bukan panggilan specialist.",
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
          "headers": {
            "Foundry-Features": "WorkflowAgents=V1Preview"
          },
          "body": {
            "items": [
              {
                "type": "message",
                "role": "assistant",
                "content": [
                  {
                    "type": "output_text",
                    "text": "KPP_ROUTE:work_iq\nKPP_STATUS:blocked\nA separate Work IQ sandbox has not been supplied. No workplace data was accessed."
                  }
                ]
              }
            ]
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "https://ai.azure.com"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {}
      },
      "why": "Penanda ini mencatat cabang/status di riwayat conversation; belum menjalankan tool atau specialist.",
      "scenario": null,
      "purpose": "Menulis penanda route/status atau pesan ke conversation."
    },
    {
      "id": "set_result_work_iq",
      "title": "set result work iq",
      "type": "SetVariable",
      "group": "Work IQ belum tersedia",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Name",
          "value": "Result"
        },
        {
          "name": "Value",
          "value": {
            "run_id": "@outputs('capture_question')?['run_id']",
            "route": "work_iq",
            "status": "blocked",
            "answer": null,
            "sources": [],
            "error": "A separate Work IQ sandbox has not been supplied. No workplace data was accessed."
          }
        }
      ],
      "input": "Object tetap yang disiapkan pada node ini.",
      "output": {
        "run_id": "<ID_SANDBOX>",
        "route": "work_iq",
        "status": "blocked",
        "answer": null,
        "sources": [],
        "error": "A separate Work IQ sandbox has not been supplied. No workplace data was accessed."
      },
      "raw": {
        "type": "SetVariable",
        "inputs": {
          "name": "Result",
          "value": {
            "run_id": "@outputs('capture_question')?['run_id']",
            "route": "work_iq",
            "status": "blocked",
            "answer": null,
            "sources": [],
            "error": "A separate Work IQ sandbox has not been supplied. No workplace data was accessed."
          }
        },
        "runAfter": {
          "blocked_work_iq": [
            "Succeeded"
          ]
        }
      },
      "why": "Response akhir membaca variabel yang disimpan, bukan otomatis mengambil output action terakhir.",
      "scenario": null,
      "purpose": "Mengisi Result dengan status blocked."
    },
    {
      "id": "ask_clarification",
      "title": "ask clarification",
      "type": "Http",
      "group": "Perlu klarifikasi",
      "url": "<ENDPOINT_FOUNDRY>/openai/v1/conversations/{conversation_id}/items",
      "url_note": "conversation_id berasal dari create_conversation.id.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "https://ai.azure.com"
        },
        {
          "name": "Foundry-Features",
          "value": "WorkflowAgents=V1Preview"
        }
      ],
      "input": {
        "items": [
          {
            "type": "message",
            "role": "assistant",
            "content": [
              {
                "type": "output_text",
                "text": "KPP_ROUTE:clarification\nKPP_STATUS:clarification\nPlease specify one topic: production, maintenance, stock, document lookup, or native knowledge retrieval."
              }
            ]
          }
        ]
      },
      "output": "Activity tersimpan di conversation. Bukan panggilan specialist.",
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
          "headers": {
            "Foundry-Features": "WorkflowAgents=V1Preview"
          },
          "body": {
            "items": [
              {
                "type": "message",
                "role": "assistant",
                "content": [
                  {
                    "type": "output_text",
                    "text": "KPP_ROUTE:clarification\nKPP_STATUS:clarification\nPlease specify one topic: production, maintenance, stock, document lookup, or native knowledge retrieval."
                  }
                ]
              }
            ]
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "https://ai.azure.com"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {}
      },
      "why": "Penanda ini mencatat cabang/status di riwayat conversation; belum menjalankan tool atau specialist.",
      "scenario": null,
      "purpose": "Menulis penanda route/status atau pesan ke conversation."
    },
    {
      "id": "set_result_clarification",
      "title": "set result clarification",
      "type": "SetVariable",
      "group": "Perlu klarifikasi",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Name",
          "value": "Result"
        },
        {
          "name": "Value",
          "value": {
            "run_id": "@outputs('capture_question')?['run_id']",
            "route": "clarification",
            "status": "clarification",
            "answer": "Please specify one topic: production, maintenance, stock, document lookup, or native knowledge retrieval.",
            "sources": [],
            "error": null
          }
        }
      ],
      "input": "Object tetap yang disiapkan pada node ini.",
      "output": {
        "run_id": "<ID_SANDBOX>",
        "route": "clarification",
        "status": "clarification",
        "answer": "Please specify one topic: production, maintenance, stock, document lookup, or native knowledge retrieval.",
        "sources": [],
        "error": null
      },
      "raw": {
        "type": "SetVariable",
        "inputs": {
          "name": "Result",
          "value": {
            "run_id": "@outputs('capture_question')?['run_id']",
            "route": "clarification",
            "status": "clarification",
            "answer": "Please specify one topic: production, maintenance, stock, document lookup, or native knowledge retrieval.",
            "sources": [],
            "error": null
          }
        },
        "runAfter": {
          "ask_clarification": [
            "Succeeded"
          ]
        }
      },
      "why": "Response akhir membaca variabel yang disimpan, bukan otomatis mengambil output action terakhir.",
      "scenario": null,
      "purpose": "Mengisi Result dengan status clarification."
    },
    {
      "id": "reject_unsupported",
      "title": "reject unsupported",
      "type": "Http",
      "group": "Di luar batas demo",
      "url": "<ENDPOINT_FOUNDRY>/openai/v1/conversations/{conversation_id}/items",
      "url_note": "conversation_id berasal dari create_conversation.id.",
      "method": "POST",
      "parameters": [
        {
          "name": "Authentication",
          "value": "Managed identity"
        },
        {
          "name": "Audience",
          "value": "https://ai.azure.com"
        },
        {
          "name": "Foundry-Features",
          "value": "WorkflowAgents=V1Preview"
        }
      ],
      "input": {
        "items": [
          {
            "type": "message",
            "role": "assistant",
            "content": [
              {
                "type": "output_text",
                "text": "KPP_ROUTE:unsupported\nKPP_STATUS:unsupported\nOnly read-only questions about the new synthetic mining demo are supported. Live systems and writes are not accessed."
              }
            ]
          }
        ]
      },
      "output": "Activity tersimpan di conversation. Bukan panggilan specialist.",
      "raw": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "@concat('<ENDPOINT_FOUNDRY>/openai/v1/conversations/',body('create_conversation')?['id'],'/items')",
          "headers": {
            "Foundry-Features": "WorkflowAgents=V1Preview"
          },
          "body": {
            "items": [
              {
                "type": "message",
                "role": "assistant",
                "content": [
                  {
                    "type": "output_text",
                    "text": "KPP_ROUTE:unsupported\nKPP_STATUS:unsupported\nOnly read-only questions about the new synthetic mining demo are supported. Live systems and writes are not accessed."
                  }
                ]
              }
            ]
          },
          "authentication": {
            "type": "ManagedServiceIdentity",
            "audience": "https://ai.azure.com"
          },
          "retryPolicy": {
            "type": "none"
          }
        },
        "runAfter": {}
      },
      "why": "Penanda ini mencatat cabang/status di riwayat conversation; belum menjalankan tool atau specialist.",
      "scenario": null,
      "purpose": "Menulis penanda route/status atau pesan ke conversation."
    },
    {
      "id": "set_result_unsupported",
      "title": "set result unsupported",
      "type": "SetVariable",
      "group": "Di luar batas demo",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Name",
          "value": "Result"
        },
        {
          "name": "Value",
          "value": {
            "run_id": "@outputs('capture_question')?['run_id']",
            "route": "unsupported",
            "status": "unsupported",
            "answer": "Only read-only questions about the new synthetic mining demo are supported. Live systems and writes are not accessed.",
            "sources": [],
            "error": null
          }
        }
      ],
      "input": "Object tetap yang disiapkan pada node ini.",
      "output": {
        "run_id": "<ID_SANDBOX>",
        "route": "unsupported",
        "status": "unsupported",
        "answer": "Only read-only questions about the new synthetic mining demo are supported. Live systems and writes are not accessed.",
        "sources": [],
        "error": null
      },
      "raw": {
        "type": "SetVariable",
        "inputs": {
          "name": "Result",
          "value": {
            "run_id": "@outputs('capture_question')?['run_id']",
            "route": "unsupported",
            "status": "unsupported",
            "answer": "Only read-only questions about the new synthetic mining demo are supported. Live systems and writes are not accessed.",
            "sources": [],
            "error": null
          }
        },
        "runAfter": {
          "reject_unsupported": [
            "Succeeded"
          ]
        }
      },
      "why": "Response akhir membaca variabel yang disimpan, bukan otomatis mengambil output action terakhir.",
      "scenario": null,
      "purpose": "Mengisi Result dengan status unsupported."
    },
    {
      "id": "Reject_invalid_request",
      "title": "Reject invalid request",
      "type": "Response",
      "group": "Penanganan error",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Status Code",
          "value": 400
        }
      ],
      "input": "Validate_request gagal atau timeout.",
      "output": {
        "error": {
          "code": "invalid_request",
          "message": "Supply a question and optional run_id only; route overrides are rejected."
        }
      },
      "raw": {
        "type": "Response",
        "kind": "Http",
        "runAfter": {
          "Validate_request": [
            "Failed",
            "TimedOut"
          ]
        },
        "inputs": {
          "statusCode": 400,
          "body": {
            "error": {
              "code": "invalid_request",
              "message": "Supply a question and optional run_id only; route overrides are rejected."
            }
          }
        }
      },
      "why": "Pemanggil HTTP perlu menerima hasil akhir atau kesalahan dari workflow.",
      "scenario": null,
      "purpose": "Mengembalikan kesalahan input tanpa memanggil agent."
    },
    {
      "id": "invalid_router_result",
      "title": "invalid router result",
      "type": "SetVariable",
      "group": "Penanganan error",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Name",
          "value": "Result"
        },
        {
          "name": "Value",
          "value": {
            "run_id": "@outputs('capture_question')?['run_id']",
            "route": "unsupported",
            "status": "failed",
            "answer": null,
            "sources": [],
            "error": "The router returned an unrecognized route. No specialist was invoked."
          }
        }
      ],
      "input": "Object tetap yang disiapkan pada node ini.",
      "output": {
        "run_id": "<ID_SANDBOX>",
        "route": "unsupported",
        "status": "failed",
        "answer": null,
        "sources": [],
        "error": "The router returned an unrecognized route. No specialist was invoked."
      },
      "raw": {
        "type": "SetVariable",
        "inputs": {
          "name": "Result",
          "value": {
            "run_id": "@outputs('capture_question')?['run_id']",
            "route": "unsupported",
            "status": "failed",
            "answer": null,
            "sources": [],
            "error": "The router returned an unrecognized route. No specialist was invoked."
          }
        },
        "runAfter": {
          "Parse_router": [
            "Failed",
            "TimedOut"
          ]
        }
      },
      "why": "Response akhir membaca variabel yang disimpan, bukan otomatis mengambil output action terakhir.",
      "scenario": null,
      "purpose": "Mengisi Result dengan status failed."
    },
    {
      "id": "default_invalid_route",
      "title": "default invalid route",
      "type": "SetVariable",
      "group": "Penanganan error",
      "url": null,
      "url_note": "",
      "method": null,
      "parameters": [
        {
          "name": "Name",
          "value": "Result"
        },
        {
          "name": "Value",
          "value": {
            "run_id": "@outputs('capture_question')?['run_id']",
            "route": "unsupported",
            "status": "failed",
            "answer": null,
            "sources": [],
            "error": "The router returned an unrecognized route. No specialist was invoked."
          }
        }
      ],
      "input": "Object tetap yang disiapkan pada node ini.",
      "output": {
        "run_id": "<ID_SANDBOX>",
        "route": "unsupported",
        "status": "failed",
        "answer": null,
        "sources": [],
        "error": "The router returned an unrecognized route. No specialist was invoked."
      },
      "raw": {
        "type": "SetVariable",
        "inputs": {
          "name": "Result",
          "value": {
            "run_id": "@outputs('capture_question')?['run_id']",
            "route": "unsupported",
            "status": "failed",
            "answer": null,
            "sources": [],
            "error": "The router returned an unrecognized route. No specialist was invoked."
          }
        },
        "runAfter": {}
      },
      "why": "Response akhir membaca variabel yang disimpan, bukan otomatis mengambil output action terakhir.",
      "scenario": null,
      "purpose": "Mengisi Result dengan status failed."
    }
  ],
  "overview": {
    "width": 1152,
    "height": 1102,
    "node_boxes": {
      "kpp_mining_start": [
        499,
        39,
        74,
        20
      ],
      "Validate_request": [
        499,
        83,
        74,
        20
      ],
      "capture_question": [
        537,
        155,
        76,
        21
      ],
      "Initialize_result": [
        537,
        198,
        76,
        22
      ],
      "Execute": [
        315,
        244,
        75,
        20
      ],
      "create_conversation": [
        315,
        288,
        75,
        20
      ],
      "classify_question": [
        315,
        332,
        75,
        20
      ],
      "record_router_response": [
        315,
        375,
        75,
        27
      ],
      "Parse_router": [
        315,
        425,
        75,
        21
      ],
      "require_completed_router": [
        315,
        469,
        75,
        27
      ],
      "router_messages": [
        315,
        518,
        75,
        23
      ],
      "router_decision": [
        315,
        563,
        75,
        21
      ],
      "route_question": [
        576,
        650,
        77,
        21
      ],
      "mark_mcp": [
        146,
        742,
        76,
        20
      ],
      "invoke_mcp": [
        146,
        786,
        76,
        20
      ],
      "normalize_mcp": [
        146,
        830,
        76,
        20
      ],
      "record_mcp_response": [
        146,
        874,
        76,
        20
      ],
      "set_result_mcp": [
        146,
        918,
        76,
        20
      ],
      "kpp_mining_end": [
        537,
        1003,
        76,
        21
      ],
      "mark_rest_api": [
        238,
        742,
        76,
        20
      ],
      "invoke_rest_api": [
        238,
        786,
        76,
        20
      ],
      "normalize_rest_api": [
        238,
        830,
        76,
        20
      ],
      "record_rest_api_response": [
        238,
        873,
        76,
        25
      ],
      "set_result_rest_api": [
        238,
        923,
        76,
        20
      ],
      "mark_knowledge": [
        330,
        742,
        76,
        20
      ],
      "invoke_knowledge": [
        330,
        786,
        76,
        20
      ],
      "normalize_knowledge": [
        330,
        830,
        76,
        20
      ],
      "record_knowledge_response": [
        330,
        873,
        76,
        25
      ],
      "set_result_knowledge": [
        330,
        923,
        76,
        20
      ],
      "mark_foundry_iq": [
        423,
        742,
        76,
        20
      ],
      "invoke_foundry_iq": [
        423,
        786,
        76,
        20
      ],
      "normalize_foundry_iq": [
        423,
        830,
        76,
        20
      ],
      "record_foundry_iq_response": [
        423,
        873,
        76,
        25
      ],
      "set_result_foundry_iq": [
        423,
        923,
        76,
        20
      ],
      "mark_fabric_data": [
        515,
        742,
        76,
        20
      ],
      "invoke_fabric_data": [
        515,
        786,
        76,
        20
      ],
      "normalize_fabric_data": [
        515,
        830,
        76,
        20
      ],
      "record_fabric_data_response": [
        515,
        873,
        76,
        25
      ],
      "set_result_fabric_data": [
        515,
        923,
        76,
        20
      ],
      "blocked_fabric_iq": [
        607,
        742,
        76,
        20
      ],
      "set_result_fabric_iq": [
        607,
        786,
        76,
        20
      ],
      "blocked_work_iq": [
        700,
        742,
        76,
        20
      ],
      "set_result_work_iq": [
        700,
        786,
        76,
        20
      ],
      "ask_clarification": [
        792,
        742,
        76,
        20
      ],
      "set_result_clarification": [
        792,
        786,
        76,
        20
      ],
      "reject_unsupported": [
        884,
        742,
        76,
        20
      ],
      "set_result_unsupported": [
        884,
        785,
        76,
        24
      ],
      "Reject_invalid_request": [
        458,
        155,
        76,
        21
      ],
      "invalid_router_result": [
        53,
        650,
        76,
        21
      ],
      "default_invalid_route": [
        1004,
        737,
        76,
        21
      ]
    },
    "image": "assets/designer/main-workflow.png"
  },
  "shots": [
    {
      "node": "kpp_mining_start",
      "width": 690,
      "height": 465,
      "caption": "Request Body JSON Schema: question wajib; run_id opsional.",
      "image": "assets/designer/parameters-request-schema.png"
    },
    {
      "node": "Validate_request",
      "width": 690,
      "height": 460,
      "caption": "Content membaca Body dari trigger, lalu Schema memeriksa bentuk datanya.",
      "image": "assets/designer/parameters-validate.png"
    },
    {
      "node": "capture_question",
      "width": 690,
      "height": 330,
      "caption": "Inputs menyatukan pertanyaan asli dengan run_id untuk langkah berikutnya.",
      "image": "assets/designer/parameters-capture-question.png"
    },
    {
      "node": "create_conversation",
      "width": 690,
      "height": 478,
      "caption": "Body membawa run_id pada metadata dan pertanyaan asli sebagai pesan user.",
      "image": "assets/designer/parameters-conversation.png"
    },
    {
      "node": "classify_question",
      "width": 690,
      "height": 370,
      "caption": "Body mengirim pertanyaan dan ID percakapan ke kppdemo-router versi 1.",
      "image": "assets/designer/parameters-classify.png"
    },
    {
      "node": "route_question",
      "width": 712,
      "height": 100,
      "caption": "On membaca field route dari hasil router. Nilai mcp memilih case MCP.",
      "image": "assets/designer/parameters-switch.png"
    },
    {
      "node": "mark_mcp",
      "width": 690,
      "height": 460,
      "caption": "Body menyimpan penanda KPP_ROUTE:mcp; node ini belum memanggil tool.",
      "image": "assets/designer/parameters-mark-mcp.png"
    },
    {
      "node": "invoke_mcp",
      "width": 690,
      "height": 370,
      "caption": "Body memakai pertanyaan dan ID percakapan yang sama untuk agent specialist MCP.",
      "image": "assets/designer/parameters-invoke-mcp-body.png"
    },
    {
      "node": "invoke_mcp",
      "width": 685,
      "height": 301,
      "caption": "Authentication memakai system-assigned managed identity dan audience Foundry.",
      "image": "assets/designer/parameters-invoke-mcp-auth.png"
    },
    {
      "node": "normalize_mcp",
      "width": 690,
      "height": 198,
      "caption": "Body mengirim run_id, route, dan respons specialist agar bukti dan sumber bisa diperiksa.",
      "image": "assets/designer/parameters-normalize-mcp.png"
    },
    {
      "node": "set_result_mcp",
      "width": 712,
      "height": 100,
      "caption": "Value mengambil Body dari normalize_mcp untuk disimpan ke Result.",
      "image": "assets/designer/parameters-set-result-mcp.png"
    },
    {
      "node": "kpp_mining_end",
      "width": 692,
      "height": 269,
      "caption": "Response mengembalikan Body dari Result serta header korelasi dan route.",
      "image": "assets/designer/parameters-response.png"
    }
  ]
};
