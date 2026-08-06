"""Sport registry contract — the single source for type semantics."""
from __future__ import annotations

from app import sports


def test_canonical_type_maps_virtual_variants():
    assert sports.canonical_type("VirtualRide") == "Ride"
    assert sports.canonical_type("VirtualRun") == "Run"
    assert sports.canonical_type("TrailRun") == "Run"
    assert sports.canonical_type("Run") == "Run"
    assert sports.canonical_type("Yoga") is None
    assert sports.canonical_type(None) is None


def test_derived_constants_match_historical_values():
    """Drop-in guarantees for the per-module copies being replaced."""
    assert sports.VALID_TYPES == ["Run", "Ride", "WeightTraining", "Workout"]
    assert sports.ENDURANCE_TYPES == {"Run", "Ride"}
    assert sports.CARDIO_TYPES >= {"Run", "Ride", "VirtualRide", "VirtualRun"}
    assert "Swim" in sports.CARDIO_TYPES
    assert sports.BIKE_TYPES == {"Ride", "VirtualRide"}
    assert sports.TYPE_EQUIV["Ride"] == {"Ride", "VirtualRide"}


def test_endurance_and_impact_classification():
    assert sports.is_endurance("VirtualRide")
    assert sports.is_endurance("Swim")
    assert not sports.is_endurance("WeightTraining")
    assert sports.is_impact("Run") and sports.is_impact("VirtualRun")
    assert not sports.is_impact("Ride")


def test_zone_source_per_sport():
    assert sports.SPORTS["Run"].zone_source == "run_hr"
    assert sports.SPORTS["Ride"].zone_source == "bike_hr"
    assert sports.SPORTS["Workout"].zone_source is None


def test_specialist_selection():
    assert sports.SPORTS["Run"].specialist == "specialist-endurance"
    assert sports.SPORTS["WeightTraining"].specialist == "specialist-complementary"
