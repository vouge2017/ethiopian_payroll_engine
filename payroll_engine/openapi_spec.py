"""OpenAPI v3 specification for EthioPayroll API."""

def get_openapi_spec():
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "EthioPayroll API",
            "description": "API for programmatic access to the Ethiopian Payroll Engine. All endpoints are tenant-isolated and require authentication.",
            "version": "1.0.0"
        },
        "servers": [
            {
                "url": "/api/v1",
                "description": "Local/Relative server path"
            }
        ],
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "Enter your API Token (ep_...)"
                }
            },
            "schemas": {
                "Employee": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "example": 12},
                        "employee_id": {"type": "string", "example": "EMP001"},
                        "name": {"type": "string", "example": "Abebe Kebede"},
                        "basic_salary": {"type": "number", "format": "float", "example": 15000.00},
                        "allowances": {"type": "number", "format": "float", "example": 2500.00},
                        "bank_or_telebirr": {"type": "string", "example": "cbe:1000123456789"}
                    }
                },
                "PayrollRun": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "example": 5},
                        "run_date": {"type": "string", "format": "date", "example": "2026-07-01"},
                        "status": {"type": "string", "example": "completed"},
                        "payslip_count": {"type": "integer", "example": 15}
                    }
                }
            }
        },
        "security": [
            {
                "bearerAuth": []
            }
        ],
        "paths": {
            "/employees": {
                "get": {
                    "summary": "List employees",
                    "description": "Returns a paginated list of employees for the active company.",
                    "parameters": [
                        {
                            "name": "page",
                            "in": "query",
                            "schema": {"type": "integer", "default": 1}
                        },
                        {
                            "name": "per_page",
                            "in": "query",
                            "schema": {"type": "integer", "default": 50}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "employees": {
                                                "type": "array",
                                                "items": {"$ref": "#/components/schemas/Employee"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "post": {
                    "summary": "Create employee",
                    "description": "Adds a new employee manually to the company's roster.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["employee_id", "name", "basic_salary"],
                                    "properties": {
                                        "employee_id": {"type": "string", "example": "EMP001"},
                                        "name": {"type": "string", "example": "Abebe Kebede"},
                                        "basic_salary": {"type": "number", "example": 15000.00},
                                        "allowances": {"type": "number", "example": 2500.00},
                                        "bank_or_telebirr": {"type": "string", "example": "cbe:1000123456789"},
                                        "tin": {"type": "string", "example": "1234567890"},
                                        "fayda_fin": {"type": "string", "example": "123456789012"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "Created",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "employee_id": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/employees/bulk": {
                "post": {
                    "summary": "Bulk import employees",
                    "description": "Import up to 500 employees in a single JSON array payload.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["employees"],
                                    "properties": {
                                        "employees": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "required": ["name", "basic_salary"],
                                                "properties": {
                                                    "employee_id": {"type": "string"},
                                                    "name": {"type": "string"},
                                                    "phone": {"type": "string"},
                                                    "basic_salary": {"type": "number"},
                                                    "allowances": {"type": "number"},
                                                    "bank_or_telebirr": {"type": "string"},
                                                    "tin": {"type": "string"},
                                                    "fayda_fin": {"type": "string"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "imported": {"type": "integer"},
                                            "total_errors": {"type": "integer"},
                                            "errors": {"type": "array", "items": {"type": "object"}}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/payroll-runs": {
                "get": {
                    "summary": "List payroll runs",
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/PayrollRun"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/payroll-runs/{run_id}/review": {
                "get": {
                    "summary": "Get payroll review (Trust Platform)",
                    "parameters": [
                        {
                            "name": "run_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "run_id": {"type": "integer"},
                                            "period": {"type": "string"},
                                            "reference": {"type": "string"},
                                            "status": {"type": "string"},
                                            "narrative": {"type": "string"},
                                            "can_approve": {"type": "boolean"},
                                            "evidence": {"type": "object"},
                                            "exceptions": {"type": "object"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
