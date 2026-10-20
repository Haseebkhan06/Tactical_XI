
import { useEffect, useMemo, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from "recharts";
import {
  Activity,
  Shield,
  Target,
  RefreshCw,
  Clock,
  ChevronRight,
  ArrowLeft,
  CalendarDays,
  MapPin,
  Trophy,
} from "lucide-react";
import RecoveryPitch from "./RecoveryPitch";
import "./App.css";

const API = "http://127.0.0.1:8011";

type TeamMetrics = {
  opponent_possessions: number;
  defensive_pressures: number;
  pressures_per_100_opponent_possessions: number | null;
  pressures_followed_by_recovery_within_5s: number;
  candidate_recovery_rate_percent: number | null;
};

type Sequence = {
  team: string;
  opponent: string;
  period?: number;
  pressure_timestamp: string;
  pressure_match_minute?: number | null;
  recovery_timestamp: string;
  recovery_match_minute?: number | null;
  seconds_to_recovery: number;
};

type MatchInfo = {
  match_id: string;
  home_team: string;
  away_team: string;
  home_score?: number | null;
  away_score?: number | null;
  match_date?: string | null;
  competition?: string | null;
  season?: string | null;
  stage?: string | null;
  data_source?: string;
  has_event_data?: boolean;
  winner?: string | null;
  result_type?: string | null;
  penalty_home_score?: number | null;
  penalty_away_score?: number | null;
  penalty_score?: string | null;
  result_note?: string | null;
};

type Analysis = {
  match: string;
  match_id?: string;
  match_metadata?: MatchInfo;
  recovery_window_seconds: number;
  teams: Record<string, TeamMetrics>;
  candidate_sequences: Sequence[];
  method_note: string;
};

type TimelinePoint = {
  minute: number;
  plotMinute: number;
  [team: string]: string | number;
};

/** Formats a winner and, where available, the penalty shootout result. */
function MatchResult({
  match,
  compact = false,
}: {
  match?: MatchInfo | null;
  compact?: boolean;
}) {
  if (!match?.winner) return null;

  const hasPenaltyScore =
    typeof match.penalty_home_score === "number" &&
    typeof match.penalty_away_score === "number";

  return (
    <div
      className={`match-result${compact ? " match-result-compact" : ""}`}
      aria-label={`Winner: ${match.winner}`}
    >
      <span className="match-result-winner">
        <Trophy size={compact ? 13 : 15} aria-hidden="true" />
        <strong>{match.winner} won</strong>
      </span>

      {hasPenaltyScore && (
        <span className="match-penalty-score">
          Pens {match.penalty_home_score}–{match.penalty_away_score}
        </span>
      )}

      {match.result_note && !compact && (
        <p className="match-result-note">{match.result_note}</p>
      )}
    </div>
  );
}

function timestampSeconds(timestamp: string): number | null {
  const match = timestamp.match(
    /^(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?$/
  );

  if (!match) return null;

  return (
    Number(match[1]) * 3600 +
    Number(match[2]) * 60 +
    Number(match[3]) +
    Number(`0.${match[4] ?? "0"}`)
  );
}

function getMatchMinute(sequence: Sequence): number | null {
  if (
    typeof sequence.pressure_match_minute === "number" &&
    Number.isFinite(sequence.pressure_match_minute)
  ) {
    return sequence.pressure_match_minute;
  }

  const seconds = timestampSeconds(sequence.pressure_timestamp);
  if (seconds === null) return null;

  // Fallback only. Backend-normalized minutes are preferred when available.
  const period = sequence.period ?? 1;

  if (period === 1) return seconds / 60;
  if (period === 2) return 45 + seconds / 60;

  return null;
}

function formatTimestamp(timestamp: string) {
  return timestamp || "—";
}

export default function App() {
  const [matches, setMatches] = useState<MatchInfo[]>([]);
  const [selectedMatchId, setSelectedMatchId] = useState<string | null>(null);
  const [data, setData] = useState<Analysis | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [matchesLoading, setMatchesLoading] = useState(true);
  const [activeSection, setActiveSection] = useState("overview");
  const [selectedTeam, setSelectedTeam] = useState("Both teams");
  const [windowMinutes, setWindowMinutes] = useState(5);

  async function loadMatches() {
    setMatchesLoading(true);
    setError("");

    try {
      const response = await fetch(`${API}/matches`);

      if (!response.ok) {
        throw new Error(`API returned HTTP ${response.status}`);
      }

      const payload: MatchInfo[] = await response.json();

      setMatches(
        payload.filter((match) => match.has_event_data !== false)
      );
    } catch (err) {
      console.error("Tactical_XI match catalogue error:", err);
      setError(
        err instanceof Error ? err.message : "Could not load matches."
      );
    } finally {
      setMatchesLoading(false);
    }
  }

  async function loadAnalysis(matchId: string) {
    setSelectedMatchId(matchId);
    setLoading(true);
    setError("");
    setData(null);
    setSelectedTeam("Both teams");
    setActiveSection("overview");

    try {
      const response = await fetch(
        `${API}/matches/${encodeURIComponent(matchId)}/pressing`
      );

      if (!response.ok) {
        const detail = await response.json().catch(() => null);

        throw new Error(
          detail?.detail || `API returned HTTP ${response.status}`
        );
      }

      setData(await response.json());
    } catch (err) {
      console.error("Tactical_XI API error:", err);
      setError(
        err instanceof Error
          ? err.message
          : "Could not connect to the backend."
      );
    } finally {
      setLoading(false);
    }
  }

  function returnToMatches() {
    setSelectedMatchId(null);
    setData(null);
    setError("");
    setLoading(false);
    setActiveSection("overview");
  }

  useEffect(() => {
    void loadMatches();
  }, []);

  const selectedMatch = matches.find(
    (match) => match.match_id === selectedMatchId
  );

  function navigateToSection(sectionId: string) {
    setActiveSection(sectionId);
    document.getElementById(sectionId)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  const teams = data ? Object.entries(data.teams) : [];

  const comparisonData = teams.map(([team, metrics]) => ({
    team,
    pressures: metrics.defensive_pressures,
    recoveries: metrics.pressures_followed_by_recovery_within_5s,
  }));

  const timelineData = useMemo<TimelinePoint[]>(() => {
    const points: TimelinePoint[] = [];

    for (let start = 0; start < 90; start += windowMinutes) {
      points.push({
        minute: start,
        plotMinute: start + windowMinutes / 2,
        ...(data
          ? Object.fromEntries(
              Object.keys(data.teams).map((team) => [team, 0])
            )
          : {}),
      });
    }

    if (!data) return points;

    for (const sequence of data.candidate_sequences) {
      const minute = getMatchMinute(sequence);

      if (minute === null || minute < 0 || minute > 90) continue;

      const safeMinute = Math.min(minute, 89.999999);
      const bucketStart =
        Math.floor(safeMinute / windowMinutes) * windowMinutes;

      const bucket = points.find(
        (point) => point.minute === bucketStart
      );

      if (bucket) {
        bucket[sequence.team] =
          Number(bucket[sequence.team] ?? 0) + 1;
      }
    }

    return points;
  }, [data, windowMinutes]);

  const visibleTimelineData = useMemo(
    () =>
      timelineData.map((point) => {
        const filtered = { ...point };

        for (const team of Object.keys(data?.teams ?? {})) {
          if (selectedTeam !== "Both teams" && selectedTeam !== team) {
            filtered[team] = 0;
          }
        }

        return filtered;
      }),
    [timelineData, selectedTeam, data]
  );

  // Match selection screen
  if (!selectedMatchId) {
    return (
      <div className="app-shell match-picker-shell">
        <main className="main-content match-picker-content">
          <header className="topbar">
            <div className="brand">
              <div className="brand-icon">
                <Activity size={24} />
              </div>
              <div>
                <h2>TACTICAL_XI</h2>
                <span>FOOTBALL INTELLIGENCE</span>
              </div>
            </div>
            <span className="picker-kicker">STATSBOMB OPEN DATA</span>
          </header>

          <section className="picker-hero">
            <p className="eyebrow">
              FOOTBALL INTELLIGENCE / MATCH LIBRARY
            </p>
            <h1>Choose your match.</h1>
            <p>
              Select a historical match to explore pressing intensity,
              candidate recoveries, team comparisons, recovery locations
              and the match timeline.
            </p>
          </section>

          {matchesLoading && (
            <div className="message">Loading available matches…</div>
          )}

          {error && (
            <div className="error-panel">
              <p>{error}</p>
              <button type="button" onClick={() => void loadMatches()}>
                Try again
              </button>
            </div>
          )}

          {!matchesLoading && !error && matches.length === 0 && (
            <div className="message">
              No matches with event data were found. Check that
              data/matches.json and the event files are present.
            </div>
          )}

          <section className="match-card-grid">
            {matches.map((match) => (
              <button
                type="button"
                className="match-choice-card"
                key={match.match_id}
                onClick={() => void loadAnalysis(match.match_id)}
              >
                <div className="match-choice-top">
                  <span className="match-tag">
                    {match.competition || "Football"}
                    {match.stage ? ` · ${match.stage}` : ""}
                  </span>
                  <ChevronRight size={18} />
                </div>

                <div className="match-choice-teams">
                  <span>{match.home_team}</span>
                  <strong>
                    {match.home_score ?? "—"} <i>:</i>{" "}
                    {match.away_score ?? "—"}
                  </strong>
                  <span>{match.away_team}</span>
                </div>

                {/* New: winner and shootout result on the match card */}
                <MatchResult match={match} compact />

                <div className="match-choice-footer">
                  <span>
                    <CalendarDays size={14} />
                    {match.match_date || "Date unavailable"}
                  </span>
                  <span>
                    View analysis <ChevronRight size={14} />
                  </span>
                </div>
              </button>
            ))}
          </section>

          <footer>
            TACTICAL_XI · Historical event data · StatsBomb Open Data
          </footer>
        </main>
      </div>
    );
  }

  if (loading && !data) {
    return (
      <div className="app-shell">
        <main className="main-content">
          <div className="message">Loading match analytics…</div>
        </main>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="app-shell">
        <main className="main-content">
          <header className="topbar">
            <div>
              <p className="eyebrow">MATCH INTELLIGENCE</p>
              <h1>Unable to load match</h1>
            </div>
            <button
              type="button"
              className="back-to-matches"
              onClick={returnToMatches}
            >
              <ArrowLeft size={15} /> All matches
            </button>
          </header>

          <div className="error-panel">
            <p>{error || "No analysis data was returned."}</p>
            <button
              type="button"
              onClick={() => void loadAnalysis(selectedMatchId)}
            >
              Try again
            </button>
          </div>
        </main>
      </div>
    );
  }

  const metadata = data.match_metadata ?? selectedMatch;
  const homeTeam = metadata?.home_team || data.match.split(" vs ")[0];
  const awayTeam = metadata?.away_team || data.match.split(" vs ")[1];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <Activity size={24} />
          </div>
          <div>
            <h2>TACTICAL_XI</h2>
            <span>FOOTBALL INTELLIGENCE</span>
          </div>
        </div>

        <p className="nav-label">WORKSPACE</p>

        <button
          type="button"
          className={`nav-item ${
            activeSection === "overview" ? "active" : ""
          }`}
          onClick={() => navigateToSection("overview")}
        >
          <Activity size={18} />
          <span>Match overview</span>
        </button>

        <button
          type="button"
          className={`nav-item ${
            activeSection === "pressing-analysis" ? "active" : ""
          }`}
          onClick={() => navigateToSection("pressing-analysis")}
        >
          <Target size={18} />
          <span>Pressing analysis</span>
        </button>

        <button
          type="button"
          className={`nav-item ${
            activeSection === "team-comparison" ? "active" : ""
          }`}
          onClick={() => navigateToSection("team-comparison")}
        >
          <Shield size={18} />
          <span>Team comparison</span>
        </button>

        <button
          type="button"
          className={`nav-item ${
            activeSection === "pressing-timeline" ? "active" : ""
          }`}
          onClick={() => navigateToSection("pressing-timeline")}
        >
          <Clock size={18} />
          <span>Match timeline</span>
        </button>

        <button
          type="button"
          className={`nav-item ${
            activeSection === "recovery-pitch" ? "active" : ""
          }`}
          onClick={() => navigateToSection("recovery-pitch")}
        >
          <MapPin size={18} />
          <span>Recovery pitch</span>
        </button>

        <div className="sidebar-bottom">
          <span className="status-dot" />
          <span>Analytics workspace</span>
          <small>v1.2</small>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">MATCH INTELLIGENCE / OVERVIEW</p>
            <h1>Pressing Dashboard</h1>
            <button
              type="button"
              className="back-to-matches"
              onClick={returnToMatches}
            >
              <ArrowLeft size={15} /> All matches
            </button>
          </div>

          <button
            type="button"
            className="refresh-button"
            onClick={() => void loadAnalysis(selectedMatchId)}
            disabled={loading}
          >
            <RefreshCw size={16} />
            {loading ? "Refreshing..." : "Refresh data"}
          </button>
        </header>

        <section id="overview" className="match-banner">
          <div>
            <span className="match-tag">
              {(metadata?.competition || "FOOTBALL").toUpperCase()}
              {metadata?.stage ? ` · ${metadata.stage.toUpperCase()}` : ""}
            </span>

            <h2>
              {homeTeam} <span>vs</span> {awayTeam}
            </h2>

            <p>
              {metadata?.match_date || "Historical match"}
              {metadata?.home_score != null &&
              metadata?.away_score != null
                ? ` · ${metadata.home_score} – ${metadata.away_score}`
                : ""}
              {" · "}
              {metadata?.data_source || "StatsBomb Open Data"}
            </p>

            {/* New: result details in the dashboard banner */}
            <MatchResult match={metadata} />
          </div>

          <div className="match-badge">
            <Activity size={24} />
          </div>
        </section>

        {loading && (
          <div className="message">Refreshing match analytics…</div>
        )}

        {error && (
          <div className="error-panel">
            <p>{error}</p>
            <button
              type="button"
              onClick={() => void loadAnalysis(selectedMatchId)}
            >
              Try again
            </button>
          </div>
        )}

        {!loading && (
          <>
            <section className="metrics-grid">
              {teams.map(([team, metrics], index) => (
                <article className="metric-card" key={team}>
                  <div className="metric-heading">
                    <span className={`team-mark team-${index}`}>
                      {team.slice(0, 1)}
                    </span>
                    <span>{team}</span>
                    <span className="metric-caption">
                      DEFENSIVE PRESSURES
                    </span>
                  </div>

                  <strong className="metric-number">
                    {metrics.defensive_pressures}
                  </strong>

                  <p className="metric-description">
                    {metrics.pressures_per_100_opponent_possessions ?? "N/A"}{" "}
                    pressures per 100 recorded opponent possessions
                  </p>
                </article>
              ))}

              <article className="metric-card compact-card">
                <div className="metric-heading">Candidate recoveries</div>
                <strong className="metric-number">
                  {data.candidate_sequences.length}
                </strong>
                <p className="metric-description">
                  Recoveries observed within {data.recovery_window_seconds}{" "}
                  seconds after a pressure
                </p>
              </article>
            </section>

            <section className="content-grid">
              <article
                id="pressing-analysis"
                className="panel chart-panel"
              >
                <div className="panel-header">
                  <div>
                    <h3>Pressing comparison</h3>
                    <p>Recorded defensive pressure events</p>
                  </div>
                  <span className="panel-icon">
                    <Activity size={18} />
                  </span>
                </div>

                <div className="chart-container">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={comparisonData} barGap={12}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        vertical={false}
                        stroke="#263244"
                      />
                      <XAxis
                        dataKey="team"
                        stroke="#94a3b8"
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        stroke="#94a3b8"
                        tickLine={false}
                        axisLine={false}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#111827",
                          border: "1px solid #334155",
                          borderRadius: 8,
                          color: "#f8fafc",
                        }}
                      />
                      <Legend />
                      <Bar
                        dataKey="pressures"
                        name="Pressures"
                        fill="#34d399"
                        radius={[4, 4, 0, 0]}
                      />
                      <Bar
                        dataKey="recoveries"
                        name="Candidate recoveries"
                        fill="#60a5fa"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </article>

              <article id="team-comparison" className="panel">
                <div className="panel-header">
                  <div>
                    <h3>Team intensity</h3>
                    <p>Pressures per 100 opponent possessions</p>
                  </div>
                </div>

                <div className="team-list">
                  {teams.map(([team, metrics], index) => {
                    const maxIntensity = Math.max(
                      1,
                      ...teams.map(
                        ([, item]) =>
                          item.pressures_per_100_opponent_possessions ?? 0
                      )
                    );

                    const intensity =
                      metrics.pressures_per_100_opponent_possessions ?? 0;

                    return (
                      <div className="team-row" key={team}>
                        <div className="team-row-top">
                          <span>{team}</span>
                          <strong>
                            {metrics.pressures_per_100_opponent_possessions ??
                              "N/A"}
                          </strong>
                        </div>

                        <div className="progress-track">
                          <div
                            className={`progress-fill fill-${index}`}
                            style={{
                              width: `${Math.min(
                                100,
                                (intensity / maxIntensity) * 100
                              )}%`,
                            }}
                          />
                        </div>

                        <p>
                          {metrics.opponent_possessions} recorded opponent
                          possessions
                        </p>
                      </div>
                    );
                  })}
                </div>
              </article>
            </section>

            <section
              id="pressing-timeline"
              className="panel timeline-panel"
            >
              <div className="panel-header">
                <div>
                  <h3>Match pressing timeline</h3>
                  <p>
                    Candidate pressure-to-recovery sequences across 0–90
                    minutes
                  </p>
                </div>
                <span className="panel-icon">
                  <Clock size={18} />
                </span>
              </div>

              <div className="timeline-controls">
                <label>
                  Team
                  <select
                    value={selectedTeam}
                    onChange={(event) =>
                      setSelectedTeam(event.target.value)
                    }
                  >
                    <option value="Both teams">Both teams</option>
                    {teams.map(([team]) => (
                      <option key={team} value={team}>
                        {team}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Window
                  <select
                    value={windowMinutes}
                    onChange={(event) =>
                      setWindowMinutes(Number(event.target.value))
                    }
                  >
                    <option value={5}>5 minutes</option>
                    <option value={15}>15 minutes</option>
                  </select>
                </label>
              </div>

              <div className="timeline-legend">
                {teams.map(([team], index) => (
                  <span className="legend-item" key={team}>
                    <span
                      className={`timeline-dot ${
                        index === 0 ? "liverpool-dot" : "madrid-dot"
                      }`}
                    />
                    {team}
                  </span>
                ))}
                <span className="legend-item halftime-label">
                  <span className="halftime-line" />
                  Half-time · 45'
                </span>
              </div>

              <div className="timeline-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={visibleTimelineData}
                    margin={{ top: 12, right: 12, bottom: 4, left: 0 }}
                    barCategoryGap="20%"
                    barGap={4}
                  >
                    <CartesianGrid
                      stroke="#253247"
                      strokeDasharray="3 5"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="plotMinute"
                      type="number"
                      domain={[0, 90]}
                      ticks={[0, 15, 30, 45, 60, 75, 90]}
                      tickFormatter={(value) => `${value}'`}
                      stroke="#8493a8"
                      tickLine={false}
                      axisLine={false}
                      tick={{ fontSize: 12 }}
                      allowDataOverflow
                    />
                    <YAxis
                      allowDecimals={false}
                      width={30}
                      stroke="#8493a8"
                      tickLine={false}
                      axisLine={false}
                      tick={{ fontSize: 12 }}
                    />
                    <Tooltip
                      labelFormatter={(value) => {
                        const center = Number(value);
                        const start = Math.max(
                          0,
                          center - windowMinutes / 2
                        );
                        const end = Math.min(
                          90,
                          center + windowMinutes / 2
                        );

                        return `${start}'–${end}'`;
                      }}
                      formatter={(value, name) => [
                        value,
                        `${name} candidate sequences`,
                      ]}
                      contentStyle={{
                        background: "#111827",
                        border: "1px solid #334155",
                        borderRadius: 8,
                        color: "#f8fafc",
                        fontSize: 12,
                      }}
                      cursor={{ fill: "rgba(148,163,184,0.07)" }}
                    />
                    <ReferenceLine
                      x={45}
                      stroke="#f59e0b"
                      strokeDasharray="4 5"
                      strokeWidth={1.5}
                    />
                    {teams.map(([team], index) => (
                      <Bar
                        key={team}
                        dataKey={team}
                        name={team}
                        fill={index === 0 ? "#34d399" : "#60a5fa"}
                        radius={[3, 3, 0, 0]}
                        maxBarSize={20}
                        isAnimationActive={false}
                      />
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <p className="method-note">
                Bars show candidate pressure-to-recovery sequences in each
                interval, not every recorded pressure event. The axis covers
                the full 90 minutes.
              </p>
            </section>

            <section id="recovery-pitch" className="recovery-section">
              <RecoveryPitch
                matchId={selectedMatchId}
                teams={Object.keys(data.teams)}
              />
            </section>

            <section className="panel sequences-panel">
              <div className="panel-header">
                <div>
                  <h3>Pressure-to-recovery sequences</h3>
                  <p>
                    Candidate recoveries observed within the defined time
                    window
                  </p>
                </div>
                <span className="sequence-count">
                  {data.candidate_sequences.length} sequences
                </span>
              </div>

              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Pressing team</th>
                      <th>Opponent</th>
                      <th>Pressure time</th>
                      <th>Recovery time</th>
                      <th>Elapsed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.candidate_sequences.map((sequence, index) => (
                      <tr
                        key={`${sequence.team}-${sequence.pressure_timestamp}-${index}`}
                      >
                        <td>
                          <strong>{sequence.team}</strong>
                        </td>
                        <td>{sequence.opponent}</td>
                        <td>
                          {formatTimestamp(sequence.pressure_timestamp)}
                        </td>
                        <td>
                          {formatTimestamp(sequence.recovery_timestamp)}
                        </td>
                        <td>{sequence.seconds_to_recovery}s</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {data.candidate_sequences.length === 0 && (
                  <p className="empty-state">
                    No candidate sequences found.
                  </p>
                )}
              </div>

              <p className="method-note">{data.method_note}</p>
            </section>
          </>
        )}

        <footer>
          TACTICAL_XI · Match analytics powered by StatsBomb Open Data
        </footer>
      </main>
    </div>
  );
}
