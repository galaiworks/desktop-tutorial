"use client";
import { useState } from "react";
import {
  personalYearFromISO,
  personalMonth,
  getPersonalYearContent,
} from "@/lib/personalYear";
import { track } from "@/lib/analytics";

const MONTHS = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"];

export default function YearPage() {
  const [birth, setBirth] = useState("");
  const [year, setYear] = useState(new Date().getFullYear());
  const [py, setPy] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  function calc() {
    setError(null);
    try {
      const n = personalYearFromISO(birth, year);
      setPy(n);
      track("result_view", { kind: "personal_year", value: n });
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const content = py ? getPersonalYearContent(py) : null;
  const thisMonth = new Date().getMonth() + 1;

  return (
    <>
      <div className="card story">
        <p className="eyebrow story">年運</p>
        <h1 className="serif">パーソナルイヤー</h1>
        <p className="muted">
          誕生日と対象の年から、いまがどんな「季節」なのかを見ます。
          9年で一巡する、人生のリズムです。
        </p>

        <label htmlFor="by" style={{ marginTop: 16 }}>
          生年月日
        </label>
        <input
          id="by"
          type="date"
          value={birth}
          min="1900-01-01"
          max="2025-12-31"
          onChange={(e) => setBirth(e.target.value)}
        />

        <label htmlFor="yr" style={{ marginTop: 18 }}>
          対象の年
        </label>
        <div className="lens-toggle" role="group" aria-label="対象の年">
          {[year - 1, year, year + 1].map((y) => (
            <button
              key={y}
              type="button"
              aria-pressed={year === y}
              onClick={() => setYear(y)}
            >
              {y}年
            </button>
          ))}
        </div>

        {error && (
          <p className="err" role="alert">
            {error}
          </p>
        )}
        <div className="btn-row">
          <button className="btn btn-primary" disabled={!birth} onClick={calc}>
            年運を見る
          </button>
        </div>
      </div>

      {content && (
        <>
          <div className="card story">
            <p className="eyebrow story">{year}年のあなた</p>
            <div style={{ textAlign: "center" }}>
              <div className="numeral" aria-hidden="true">
                {content.year}
              </div>
              <p className="type-name">{content.theme}</p>
            </div>
            <p>{content.summary}</p>
          </div>

          <div className="card science">
            <p className="eyebrow science">この年の過ごし方</p>
            <table className="score-table">
              <tbody>
                <tr>
                  <th scope="row" style={{ verticalAlign: "top", width: "6.5em" }}>
                    向いていること
                  </th>
                  <td>{content.dos.join("／")}</td>
                </tr>
                <tr>
                  <th scope="row" style={{ verticalAlign: "top" }}>
                    急がなくてよいこと
                  </th>
                  <td>{content.donts.join("／")}</td>
                </tr>
                <tr>
                  <th scope="row" style={{ verticalAlign: "top" }}>
                    恋愛
                  </th>
                  <td>{content.love}</td>
                </tr>
                <tr>
                  <th scope="row" style={{ verticalAlign: "top" }}>
                    仕事
                  </th>
                  <td>{content.work}</td>
                </tr>
              </tbody>
            </table>
            <p className="muted" style={{ marginTop: 14 }}>
              今月（{MONTHS[thisMonth - 1]}）のパーソナルマンスは
              <b> {personalMonth(content.year, thisMonth)} </b>
              です。
            </p>
          </div>
        </>
      )}

      <p className="notice">
        パーソナルイヤーは「誕生月 + 誕生日 + 対象年」を1桁まで還元して算出しています。
        {content?.disclaimer}
        本診断は娯楽・自己理解を目的としたもので、結果を保証するものではありません。
      </p>
    </>
  );
}
