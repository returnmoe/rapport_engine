agent = {
    "type": "object",
    "properties": {
        "kind": {"const": "RapportAgent"},
        "apiVersion": {"const": "engine.rapport.return.moe/v1beta1"},
        "metadata": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"}
            },
            "required": ["name"],
        },
        "spec": {
            "type": "object",
            "properties": {
                "activation": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"enum": ["reply", "keyword"]},
                            "value": {"type": "string"},
                        },
                        "required": ["type"],
                        "if": {"properties": {"type": {"const": "keyword"}}},
                        "then": {"required": ["value"]},
                    },
                },
                "admin": {"type": "array", "items": {"type": "string"}},
                "history": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "maxStorageSize": {"type": "integer"},
                            "maxChainSize": {"type": "integer"},
                        },
                        "required": [
                            "source",
                            "maxStorageSize",
                            "maxChainSize",
                        ],
                    },
                },
                "messages": {
                    "type": "object",
                    "properties": {
                        "limits": {
                            "type": "object",
                            "properties": {
                                "daily": {
                                    "type": "object",
                                    "properties": {
                                        "tokens": {"type": "integer"}
                                    },
                                },
                                "input": {
                                    "type": "object",
                                    "properties": {
                                        "tokens": {
                                            "type": "integer",
                                            "maximum": 8192,
                                        },
                                        "action": {
                                            "enum": ["truncate", "reject"]
                                        },
                                    },
                                    "required": ["tokens", "action"],
                                },
                                "output": {
                                    "type": "object",
                                    "properties": {
                                        "tokens": {
                                            "type": "integer",
                                            "maximum": 8192,
                                        },
                                        "action": {"const": "truncate"},
                                    },
                                    "required": ["tokens", "action"],
                                },
                                "user": {
                                    "type": "object",
                                    "properties": {
                                        "interactions": {
                                            "type": "integer",
                                            "maximum": 65536,
                                        },
                                        "window": {"type": "string"},
                                    },
                                },
                            },
                            "required": ["input", "output"],
                        },
                        "errors": {
                            "type": "object",
                            "properties": {
                                "generic": {"type": "string"},
                                "dailyLimitExceeded": {"type": "string"},
                                "rateLimitExceeded": {"type": "string"},
                            },
                            "required": [
                                "generic",
                                "dailyLimitExceeded",
                                "rateLimitExceeded",
                            ],
                        },
                    },
                    "required": ["limits", "errors"],
                },
                "model": {"type": "string"},
                "prompts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "role": {"enum": ["assistant", "system", "user"]},
                        },
                        "required": ["content", "role"],
                    },
                },
            },
            "required": [
                "activation",
                "admin",
                "history",
                "messages",
                "model",
                "prompts",
            ],
        },
    },
    "required": ["kind", "apiVersion", "metadata", "spec"],
}
