from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ── Airport Search ────────────────────────────────────────────────────

class AirportResult(BaseModel):
    iata: str
    name: str
    city: str
    state: str
    hub_size: str
    runways: int
    estimated_annual_pax: int


# ── Airport Stats ─────────────────────────────────────────────────────

class AirportMetrics(BaseModel):
    load_factor: Optional[float] = None
    utilization: Optional[float] = None
    pax_growth: Optional[float] = None
    congestion: Optional[float] = None
    long_haul_ratio: Optional[float] = None
    unmet_demand: Optional[float] = None


class TopRoute(BaseModel):
    destination: str
    passengers: int
    flights: int


class AirportStats(BaseModel):
    iata: str
    name: str
    year: int
    total_passengers: int
    total_seats: int
    departures_performed: int
    departures_scheduled: int
    total_freight: int
    metrics: AirportMetrics
    top_routes: list[TopRoute]
    data_vintage: str


# ── Comparison ────────────────────────────────────────────────────────

class ComparisonAirport(BaseModel):
    iata: str
    name: str
    year: int
    total_passengers: int
    metrics: AirportMetrics


class RankingEntry(BaseModel):
    iata: str
    value: float
    rank: int


class ComparisonResult(BaseModel):
    airports: list[ComparisonAirport]
    rankings: dict[str, list[RankingEntry]]
    year: int
    data_vintage: str


# ── Scoring ───────────────────────────────────────────────────────────

class ScoredAirportResponse(BaseModel):
    iata: str
    name: str
    ios_total: float
    component_scores: dict[str, Optional[float]]
    raw_metrics: dict[str, Optional[float]]
    confidence: Literal["high", "medium", "low"]
    data_vintage: str
    available_components: int


class ScoreResult(BaseModel):
    ranked: list[ScoredAirportResponse]
    weights_used: dict[str, float]
    year: int
    data_vintage: str


# ── Flight Breakdown ──────────────────────────────────────────────────

class CarrierInfo(BaseModel):
    carrier: str
    flights: int


class FlightBreakdown(BaseModel):
    iata: str
    name: str
    year: int
    total_flights: int
    distance_breakdown: dict[str, int]
    distance_percentages: dict[str, float]
    top_carriers: list[CarrierInfo]
    top_destinations: list[TopRoute]
    data_vintage: str


# ── Demand Analysis ───────────────────────────────────────────────────

class CapacityYear(BaseModel):
    year: int
    passengers: int
    seats: int
    departures: int


class MSAInfo(BaseModel):
    msa_name: Optional[str] = None
    latest_population: Optional[int] = None
    population_cagr: Optional[float] = None


class DemandAnalysis(BaseModel):
    iata: str
    name: str
    capacity_trend: list[CapacityYear]
    capacity_growth_yoy: Optional[float] = None
    msa_info: MSAInfo
    unmet_demand: Optional[float] = None
    assessment: str
    saturation_indicators: list[str]
    data_vintage: str


# ── Chat (for M4) ────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    history: list[dict] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    tools_called: list[str] = Field(default_factory=list)
    data_vintage: str = ""
    assumptions: list[str] = Field(default_factory=list)


# ── Score/Compare API requests ────────────────────────────────────────

class ScoreRequest(BaseModel):
    codes: list[str]
    weights: Optional[dict[str, float]] = None


class CompareRequest(BaseModel):
    codes: list[str]
    metrics: Optional[list[str]] = None
