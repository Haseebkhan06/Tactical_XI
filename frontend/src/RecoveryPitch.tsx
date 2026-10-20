
import { useEffect, useMemo, useState } from "react";
import { MapPin, RefreshCw } from "lucide-react";

const API = "http://127.0.0.1:8011";

type Recovery = {
  event_id?: string | number;
  event_index?: number;
  team: string;
  period: number;
  timestamp: string;
  location: number[] | null;
  player?: string | null;
};

type RecoveryResponse = {
  match_id: string;
  match?: string;
  count: number;
  recoveries: Recovery[];
};

type Props = {
  matchId: string;
  teams: string[];
};

type RecoveryWithKey = Recovery & { _key: string };

function formatTime(timestamp: string, period: number) {
  const parts = timestamp.split(":");
  if (parts.length < 3) return timestamp;

  const minutes = Number(parts[1]);
  const seconds = Number(parts[2]);

  if (!Number.isFinite(minutes) || !Number.isFinite(seconds)) {
    return timestamp;
  }

  return `P${period} · ${String(minutes).padStart(2, "0")}:${String(
    Math.floor(seconds)
  ).padStart(2, "0")}`;
}

function isValidLocation(location: number[] | null) {
  return (
    Array.isArray(location) &&
    location.length >= 2 &&
    Number.isFinite(Number(location[0])) &&
    Number.isFinite(Number(location[1])) &&
    Number(location[0]) >= 0 &&
    Number(location[0]) <= 120 &&
    Number(location[1]) >= 0 &&
    Number(location[1]) <= 80
  );
}

export default function RecoveryPitch({ matchId, teams }: Props) {
  const [payload, setPayload] = useState<RecoveryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [teamFilter, setTeamFilter] = useState("All teams");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function loadRecoveries() {
      setLoading(true);
      setError("");
      setPayload(null);
      setSelectedId(null);
      setTeamFilter("All teams");

      try {
        const response = await fetch(
          `${API}/matches/${encodeURIComponent(matchId)}/recoveries`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          const detail = await response.json().catch(() => null);
          throw new Error(
            detail?.detail ||
              `Recovery endpoint returned HTTP ${response.status}`
          );
        }

        const result: RecoveryResponse = await response.json();
        setPayload(result);
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") return;

        setError(
          err instanceof Error ? err.message : "Could not load recoveries."
        );
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void loadRecoveries();
    return () => controller.abort();
  }, [matchId, reloadKey]);

  const recoveries = useMemo<RecoveryWithKey[]>(
    () =>
      (payload?.recoveries ?? []).map((recovery, index) => ({
        ...recovery,
        _key: String(
          recovery.event_id ??
            recovery.event_index ??
            `${recovery.team}-${index}`
        ),
      })),
    [payload]
  );

  const visibleRecoveries = useMemo(
    () =>
      recoveries.filter(
        (recovery) =>
          teamFilter === "All teams" || recovery.team === teamFilter
      ),
    [recoveries, teamFilter]
  );

  const plottedRecoveries = useMemo(
    () =>
      visibleRecoveries.filter((recovery) =>
        isValidLocation(recovery.location)
      ),
    [visibleRecoveries]
  );

  const selectedRecovery =
    visibleRecoveries.find((recovery) => recovery._key === selectedId) ?? null;

  const teamColor = (team: string) =>
    teams.indexOf(team) === 0 ? "#34d399" : "#60a5fa";

  function selectRecovery(recovery: RecoveryWithKey) {
    setSelectedId(recovery._key);
  }

  return (
    <section id="recovery-pitch" className="panel recovery-panel">
      <header className="panel-header recovery-heading">
        <div>
          <h3>Recovery pitch</h3>
          <p>Recorded ball recoveries plotted at their event locations</p>
        </div>

        <span className="recovery-heading-icon" aria-hidden="true">
          <MapPin size={19} />
        </span>
      </header>

      {loading && (
        <div className="recovery-message">
          <span className="recovery-spinner" aria-hidden="true" />
          Loading recorded recovery events…
        </div>
      )}

      {!loading && error && (
        <div className="recovery-message recovery-error">
          <p>{error}</p>
          <button
            type="button"
            className="recovery-retry"
            onClick={() => setReloadKey((key) => key + 1)}
          >
            <RefreshCw size={14} />
            Retry loading
          </button>
        </div>
      )}

      {!loading && !error && payload && (
        <>
          <div className="recovery-toolbar">
            <div className="recovery-stat">
              <strong>{visibleRecoveries.length}</strong>
              <span>recorded recoveries</span>
              <span className="recovery-stat-secondary">
                {plottedRecoveries.length} plotted
              </span>
            </div>

            <label className="recovery-filter">
              <span>Team</span>
              <select
                value={teamFilter}
                onChange={(event) => {
                  setTeamFilter(event.target.value);
                  setSelectedId(null);
                }}
              >
                <option value="All teams">All teams</option>
                {teams.map((team) => (
                  <option key={team} value={team}>
                    {team}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="recovery-layout">
            <div className="recovery-pitch-column">
              <div className="recovery-pitch-wrap">
                <svg
                  className="recovery-pitch"
                  viewBox="0 0 600 400"
                  role="img"
                  aria-label="Football pitch showing recorded ball-recovery locations"
                >
                  <defs>
                    <pattern
                      id="recovery-pitch-stripes"
                      width="100"
                      height="400"
                      patternUnits="userSpaceOnUse"
                    >
                      <rect width="50" height="400" fill="#14532d" />
                      <rect x="50" width="50" height="400" fill="#166534" />
                    </pattern>
                  </defs>

                  <rect
                    x="0"
                    y="0"
                    width="600"
                    height="400"
                    rx="5"
                    fill="url(#recovery-pitch-stripes)"
                  />

                  <g
                    fill="none"
                    stroke="rgba(226,255,236,0.82)"
                    strokeWidth="2"
                  >
                    <rect x="10" y="10" width="580" height="380" />
                    <line x1="300" y1="10" x2="300" y2="390" />
                    <circle cx="300" cy="200" r="61.5" />
                    <circle cx="300" cy="200" r="2.5" fill="#e2ffec" />

                    <rect x="10" y="105" width="96" height="190" />
                    <rect x="10" y="145" width="38" height="110" />
                    <circle cx="77" cy="200" r="2.5" fill="#e2ffec" />
                    <path d="M106 157 A61.5 61.5 0 0 1 106 243" />

                    <rect x="494" y="105" width="96" height="190" />
                    <rect x="552" y="145" width="38" height="110" />
                    <circle cx="523" cy="200" r="2.5" fill="#e2ffec" />
                    <path d="M494 157 A61.5 61.5 0 0 0 494 243" />

                    <path d="M10 32 A22 22 0 0 0 32 10" />
                    <path d="M568 10 A22 22 0 0 0 590 32" />
                    <path d="M10 368 A22 22 0 0 1 32 390" />
                    <path d="M568 390 A22 22 0 0 1 590 368" />
                  </g>

                  {plottedRecoveries.map((recovery) => {
                    const x = (Number(recovery.location![0]) / 120) * 600;
                    const y = (Number(recovery.location![1]) / 80) * 400;
                    const selected = recovery._key === selectedId;

                    return (
                      <g
                        key={recovery._key}
                        role="button"
                        tabIndex={0}
                        aria-label={`Recovery by ${recovery.team}${
                          recovery.player ? `, ${recovery.player}` : ""
                        } at ${formatTime(
                          recovery.timestamp,
                          recovery.period
                        )}`}
                        className="recovery-point"
                        onClick={() => selectRecovery(recovery)}
                        onMouseEnter={() => setSelectedId(recovery._key)}
                        onFocus={() => setSelectedId(recovery._key)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            selectRecovery(recovery);
                          }
                        }}
                      >
                        {selected && (
                          <circle
                            cx={x}
                            cy={y}
                            r="13"
                            fill={teamColor(recovery.team)}
                            opacity="0.25"
                          />
                        )}

                        <circle
                          cx={x}
                          cy={y}
                          r={selected ? 7 : 5}
                          fill={teamColor(recovery.team)}
                          stroke={selected ? "#ffffff" : "#0b1420"}
                          strokeWidth={selected ? 2.5 : 1.5}
                        />
                      </g>
                    );
                  })}
                </svg>
              </div>

              <div className="recovery-legend">
                {teams.map((team) => (
                  <span key={team}>
                    <i style={{ background: teamColor(team) }} />
                    {team}
                  </span>
                ))}
              </div>

              <p className="recovery-caption">
                Coordinates use the StatsBomb 120 × 80 pitch system. Events
                without valid recorded locations remain in the event list but
                are not plotted.
              </p>
            </div>

            <aside className="recovery-event-column">
              <header className="recovery-list-heading">
                <div>
                  <h4>Recovery events</h4>
                  <p>
                    {visibleRecoveries.length} events
                    {teamFilter !== "All teams" ? ` · ${teamFilter}` : ""}
                  </p>
                </div>
              </header>

              {visibleRecoveries.length === 0 ? (
                <p className="recovery-empty">
                  No recorded recoveries found for this filter.
                </p>
              ) : (
                <div className="recovery-event-list">
                  {visibleRecoveries.map((recovery, index) => {
                    const hasLocation = isValidLocation(recovery.location);
                    const selected = recovery._key === selectedId;

                    return (
                      <button
                        type="button"
                        key={recovery._key}
                        className={`recovery-event ${
                          selected ? "selected" : ""
                        }`}
                        aria-pressed={selected}
                        onClick={() => selectRecovery(recovery)}
                        onMouseEnter={() => setSelectedId(recovery._key)}
                      >
                        <span className="recovery-event-number">
                          {String(index + 1).padStart(2, "0")}
                        </span>

                        <span
                          className="recovery-event-marker"
                          style={{ background: teamColor(recovery.team) }}
                          aria-hidden="true"
                        />

                        <span className="recovery-event-details">
                          <strong>{recovery.team}</strong>
                          <span>
                            {recovery.player || "Player not recorded"}
                          </span>
                          <span className="recovery-event-time">
                            {formatTime(
                              recovery.timestamp,
                              recovery.period
                            )}
                            {!hasLocation ? " · No location" : ""}
                          </span>
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}

              {selectedRecovery && (
                <div className="recovery-detail">
                  <span className="recovery-detail-label">
                    SELECTED EVENT
                  </span>
                  <strong>{selectedRecovery.team}</strong>
                  <p>
                    {selectedRecovery.player || "Player not recorded"}
                  </p>
                  <p>
                    {formatTime(
                      selectedRecovery.timestamp,
                      selectedRecovery.period
                    )}
                  </p>
                  <p>
                    Location:{" "}
                    {isValidLocation(selectedRecovery.location)
                      ? `${selectedRecovery.location![0]}, ${selectedRecovery.location![1]}`
                      : "Not recorded"}
                  </p>
                </div>
              )}
            </aside>
          </div>
        </>
      )}
    </section>
  );
}
