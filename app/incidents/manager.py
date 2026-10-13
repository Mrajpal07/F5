
from dataclasses import dataclass, field

from app.history.store import DEFAULT_DB_PATH
from app.incidents.store import (
    initialize_incident_store,
    load_active_incidents,
    load_detection_states,
    save_detection_state,
    save_incident,
)


FAILURES_TO_OPEN = 3
ANOMALIES_TO_DEGRADE = 3
SUCCESSES_TO_RESOLVE = 2


@dataclass
class Incident:
    target: str
    category: str
    severity: str
    status: str = "active"
    failure_count: int = 0
    anomaly_count: int = 0
    recovery_count: int = 0
    evidence: list[dict] = field(default_factory=list)
    incident_id: int | None = None


class IncidentManager:
    """Manage persistent incident state transitions for each target."""

    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = db_path

        initialize_incident_store(self.db_path)

        self.active_incidents = {}
        self.failure_streaks = {}
        self.anomaly_streaks = {}
        self.recovery_streaks = {}
        self.failure_evidence = {}
        self.anomaly_evidence = {}

        for target, state in load_detection_states(self.db_path).items():
            self.failure_streaks[target] = state["failure_streak"]
            self.anomaly_streaks[target] = state["anomaly_streak"]
            self.failure_evidence[target] = state["failure_evidence"]
            self.anomaly_evidence[target] = state["anomaly_evidence"]


        # Restore active incidents from SQLite.
        for item in load_active_incidents(self.db_path):
            incident = Incident(
                target=item["target"],
                category=item["category"],
                severity=item["severity"],
                status=item["status"],
                failure_count=item["failure_count"],
                anomaly_count=item["anomaly_count"],
                recovery_count=item["recovery_count"],
                evidence=item["evidence"],
                incident_id=item["id"],
            )

            self.active_incidents[
                (incident.target, incident.category)
            ] = incident
    def _persist_detection_state(self, target):
        """Save the current detection streaks and evidence to SQLite."""
        save_detection_state(
            target=target,
            failure_streak=self.failure_streaks.get(target, 0),
            anomaly_streak=self.anomaly_streaks.get(target, 0),
            failure_evidence=self.failure_evidence.get(target, []),
            anomaly_evidence=self.anomaly_evidence.get(target, []),
            db_path=self.db_path,
        )

    def process_observation(
        self,
        target,
        observation,
        is_anomaly=False,
    ):
        status_code = observation.get("status")
        failure_type = observation.get("failure_type")

        successful = (
            status_code is not None
            and 200 <= status_code < 300
            and failure_type is None
        )

        category = None

        if not successful:
            category = "availability"
            self.failure_streaks[target] = (
                self.failure_streaks.get(target, 0) + 1
            )
            self.anomaly_streaks[target] = 0
            self.recovery_streaks[target] = 0

            self.anomaly_evidence[target] = []
            self.failure_evidence.setdefault(target, []).append(
                dict(observation)
            )
            self.failure_evidence[target] = (
                self.failure_evidence[target][-FAILURES_TO_OPEN:]
            )

        elif is_anomaly is True:
            category = "latency"
            self.anomaly_streaks[target] = (
                self.anomaly_streaks.get(target, 0) + 1
            )
            self.failure_streaks[target] = 0
            self.recovery_streaks[target] = 0

            self.failure_evidence[target] = []
            self.anomaly_evidence.setdefault(target, []).append(
                dict(observation)
            )
            self.anomaly_evidence[target] = (
                self.anomaly_evidence[target][-ANOMALIES_TO_DEGRADE:]
            )

        elif is_anomaly is False:
            self.failure_streaks[target] = 0
            self.anomaly_streaks[target] = 0
            self.recovery_streaks[target] = (
                self.recovery_streaks.get(target, 0) + 1
            )

            self.failure_evidence[target] = []
            self.anomaly_evidence[target] = []

        # Handle availability or latency incident creation and updates.
        if category is not None:
            incident_key = (target, category)
            incident = self.active_incidents.get(incident_key)

            threshold = (
                FAILURES_TO_OPEN
                if category == "availability"
                else ANOMALIES_TO_DEGRADE
            )

            streak = (
                self.failure_streaks[target]
                if category == "availability"
                else self.anomaly_streaks[target]
            )

            if incident is None and streak >= threshold:
                incident = Incident(
                    target=target,
                    category=category,
                    severity=(
                        "high"
                        if category == "availability"
                        else "medium"
                    ),
                )

                # Include all observations that triggered the incident.
                if category == "availability":
                    incident.evidence = list(
                        self.failure_evidence.get(target, [])
                    )
                else:
                    incident.evidence = list(
                        self.anomaly_evidence.get(target, [])
                    )

                self.active_incidents[incident_key] = incident

            if incident is not None:
                # Avoid duplicating the observation that opened the incident.
                if not (
                    incident.evidence
                    and incident.evidence[-1] == observation
                ):
                    incident.evidence.append(dict(observation))

                incident.failure_count = self.failure_streaks[target]
                incident.anomaly_count = self.anomaly_streaks[target]
                incident.recovery_count = 0

                save_incident(incident, self.db_path)
            self._persist_detection_state(target)
            return incident

        # Unknown latency: preserve latency incidents without advancing
        # their recovery, but allow successful HTTP probes to recover
        # availability incidents.
        if successful and is_anomaly is None:
            self.failure_streaks[target] = 0
            self.anomaly_streaks[target] = 0
            self.failure_evidence[target] = []
            self.anomaly_evidence[target] = []

            resolved = []

            resolved = []

            for incident_key, incident in list(
                self.active_incidents.items()
            ):
                if incident.target != target:
                    continue

                incident.evidence.append(dict(observation))

                if incident.category == "latency":
                    save_incident(incident, self.db_path)
                    continue

                incident.recovery_count += 1

                if incident.recovery_count >= SUCCESSES_TO_RESOLVE:
                    incident.status = "resolved"
                    save_incident(incident, self.db_path)
                    resolved.append(incident)
                    del self.active_incidents[incident_key]
                else:
                    save_incident(incident, self.db_path)

            self._persist_detection_state(target)
            return resolved[-1] if resolved else None

        # A normal observation can advance recovery for active incidents.
        resolved = []

        for incident_key, incident in list(
            self.active_incidents.items()
        ):
            if incident.target != target:
                continue

            incident.recovery_count += 1
            incident.evidence.append(dict(observation))

            if incident.recovery_count >= SUCCESSES_TO_RESOLVE:
                incident.status = "resolved"
                save_incident(incident, self.db_path)
                resolved.append(incident)
                del self.active_incidents[incident_key]
            else:
                save_incident(incident, self.db_path)

        self._persist_detection_state(target)
        return resolved[-1] if resolved else None
