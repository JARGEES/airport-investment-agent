from __future__ import annotations

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_airports",
            "description": (
                "Search for US airports by region, state, minimum passenger volume, "
                "or hub type. Returns a list of matching airports with basic metadata. "
                "Use this to find airports that match criteria before scoring or comparing them."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": (
                            "US region name (e.g., 'New England', 'Southeast', 'Pacific West', "
                            "'Mid-Atlantic', 'Midwest', 'Southwest', 'Mountain West', "
                            "'Great Plains', 'Alaska', 'Hawaii')"
                        ),
                    },
                    "state": {
                        "type": "string",
                        "description": "Two-letter state code (e.g., 'CA', 'NY', 'TX')",
                    },
                    "min_passengers": {
                        "type": "integer",
                        "description": "Minimum annual passenger volume filter",
                    },
                    "airport_type": {
                        "type": "string",
                        "description": "Hub classification: 'large_hub', 'medium_hub', 'small_hub', or 'non_hub'",
                        "enum": ["large_hub", "medium_hub", "small_hub", "non_hub"],
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_airport_stats",
            "description": (
                "Get detailed statistics and KPIs for a single airport. Returns passenger volume, "
                "seat capacity, departure counts, all six investment metrics (load factor, utilization, "
                "passenger growth, congestion, long-haul ratio, unmet demand), and top routes. "
                "Use this for deep analysis of a specific airport."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "iata_code": {
                        "type": "string",
                        "description": "IATA airport code (e.g., 'BOS', 'LAX', 'SFO')",
                    },
                    "year": {
                        "type": "integer",
                        "description": "Data year (defaults to most recent available)",
                    },
                },
                "required": ["iata_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_airports",
            "description": (
                "Compare multiple airports side-by-side on selected metrics. Returns each airport's "
                "metric values plus rankings showing which airport leads on each metric. "
                "Use this when the user asks to compare specific airports."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of IATA codes to compare (e.g., ['LAX', 'SFO', 'SAN'])",
                    },
                    "metrics": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "load_factor",
                                "utilization",
                                "pax_growth",
                                "congestion",
                                "long_haul_ratio",
                                "unmet_demand",
                            ],
                        },
                        "description": "Specific metrics to compare (defaults to all six if omitted)",
                    },
                },
                "required": ["codes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "score_airports",
            "description": (
                "Compute the Investment Opportunity Score (IOS) for a set of airports and rank them. "
                "The IOS is a composite 0-100 score based on load factor, utilization, passenger growth, "
                "congestion, long-haul ratio, and unmet demand. Returns ranked results with per-component "
                "breakdowns and confidence levels. Use this to identify top investment candidates."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of IATA codes to score (e.g., ['BOS', 'BDL', 'PVD', 'MHT'])",
                    },
                    "weights": {
                        "type": "object",
                        "description": (
                            "Custom weights for scoring components. Keys: 'load_factor', 'utilization', "
                            "'pax_growth', 'congestion', 'long_haul_ratio', 'unmet_demand'. "
                            "Values should sum to 1.0. Defaults: growth=0.25, load/util=0.20, "
                            "congestion=0.15, long_haul/unmet=0.10"
                        ),
                        "properties": {
                            "load_factor": {"type": "number"},
                            "utilization": {"type": "number"},
                            "pax_growth": {"type": "number"},
                            "congestion": {"type": "number"},
                            "long_haul_ratio": {"type": "number"},
                            "unmet_demand": {"type": "number"},
                        },
                    },
                },
                "required": ["codes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_flight_breakdown",
            "description": (
                "Get the flight distribution for an airport: short/medium/long-haul breakdown, "
                "top carriers, and top destinations by passenger volume. Use this to understand "
                "an airport's route mix and which distance categories dominate."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "iata_code": {
                        "type": "string",
                        "description": "IATA airport code (e.g., 'ANC', 'LAX')",
                    },
                    "year": {
                        "type": "integer",
                        "description": "Data year (defaults to most recent available)",
                    },
                },
                "required": ["iata_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_demand_analysis",
            "description": (
                "Analyze unmet flight demand for an airport by comparing its capacity growth against "
                "regional population growth. Returns historical capacity trend, MSA population data, "
                "the demand gap, a qualitative assessment, and saturation indicators. "
                "Use this when the user asks about demand, capacity constraints, or growth potential."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "iata_code": {
                        "type": "string",
                        "description": "IATA airport code (e.g., 'SFO', 'ATL')",
                    },
                },
                "required": ["iata_code"],
            },
        },
    },
]
