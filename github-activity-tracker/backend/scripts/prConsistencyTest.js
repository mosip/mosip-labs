/**
 * Deeper PR-count consistency checks across summary / users / user-details / activity.
 */
require('dotenv').config();
const axios = require('axios');
const pool = require('../db/dbPool');

const BASE = 'http://localhost:3000';
let pass = 0;
let fail = 0;

function ok(n, d) { pass++; console.log(`  ✓ ${n}${d ? ' — ' + d : ''}`); }
function bad(n, d) { fail++; console.log(`  ✗ ${n} — ${d}`); }

async function get(path, params) {
  return axios.get(`${BASE}${path}`, { params, validateStatus: () => true, timeout: 60000 });
}

async function main() {
  console.log('PR consistency deep-dive\n');

  const orgs = ['mosip', 'inji'];
  const periods = ['weekly', 'monthly', 'yearly'];
  const roles = (await get('/user-roles')).data.map((r) => r.name);

  // 1) Activity arrays: labels length == series length; totals align
  console.log('=== Activity series integrity ===');
  for (const org of orgs) {
    for (const period of periods) {
      const res = await get(`/orgs/${org}/activity`, { period });
      const d = res.data;
      const n = d.labels?.length;
      const okLen =
        d.commits?.length === n &&
        d.prs?.length === n &&
        d.reviews?.length === n &&
        d.total?.length === n;
      if (okLen) ok(`activity lengths ${org} ${period}`, `${n} buckets`);
      else bad(`activity lengths ${org} ${period}`, JSON.stringify({ n, c: d.commits?.length, p: d.prs?.length }));

      // each total[i] should equal prs[i]+reviews[i] (or commits too — check which)
      let mathOk = true;
      let usesCommits = false;
      for (let i = 0; i < n; i++) {
        const prRev = Number(d.prs[i]) + Number(d.reviews[i]);
        const all = prRev + Number(d.commits[i]);
        if (Number(d.total[i]) === all) usesCommits = true;
        else if (Number(d.total[i]) !== prRev && Number(d.total[i]) !== all) mathOk = false;
      }
      if (mathOk) ok(`activity total math ${org} ${period}`, usesCommits ? 'total=commits+prs+reviews' : 'total=prs+reviews');
      else bad(`activity total math ${org} ${period}`, 'mismatch');

      const sumPrs = d.prs.reduce((a, b) => a + Number(b), 0);
      ok(`activity PR sum ${org} ${period}`, String(sumPrs));
    }
  }

  // 2) For top users by PR yearly, user-details.summary.prs must match users list prs
  console.log('\n=== User list vs user-details PR match ===');
  for (const org of orgs) {
    for (const period of ['monthly', 'yearly']) {
      const listRes = await get(`/orgs/${org}/users`, {
        period,
        page: 1,
        limit: 5,
        sortBy: 'prs',
        sortOrder: 'desc',
      });
      const users = Array.isArray(listRes.data) ? listRes.data : listRes.data.users || [];
      for (const u of users.slice(0, 5)) {
        const det = await get(`/orgs/${org}/users/${u.login}`, { period });
        if (det.status !== 200) {
          bad(`details ${org}/${u.login} ${period}`, `status=${det.status}`);
          continue;
        }
        const detailPrs = Number(det.data.summary?.prs);
        const listPrs = Number(u.prs);
        if (detailPrs === listPrs) ok(`${org}/${u.login} ${period} prs`, String(listPrs));
        else bad(`${org}/${u.login} ${period} prs`, `list=${listPrs} details=${detailPrs}`);
      }
    }
  }

  // 3) Summary role=all PR >= each individual role PR (monthly)
  console.log('\n=== Role filter PR subset check ===');
  for (const org of orgs) {
    const allRes = await get(`/orgs/${org}/summary`, { period: 'monthly', role: 'all' });
    const allPrs = Number(allRes.data.total_prs);
    ok(`${org} monthly all prs`, String(allPrs));
    for (const role of roles) {
      const r = await get(`/orgs/${org}/summary`, { period: 'monthly', role });
      if (r.status !== 200) {
        bad(`${org} role=${role}`, `status=${r.status}`);
        continue;
      }
      const prs = Number(r.data.total_prs);
      if (prs <= allPrs) ok(`${org} role=${role} prs<=all`, `${prs} <= ${allPrs}`);
      else bad(`${org} role=${role} prs<=all`, `${prs} > ${allPrs}`);
    }
  }

  // 4) Leaderboard PR fields present and scores non-negative
  console.log('\n=== Leaderboard score sanity ===');
  for (const org of orgs) {
    const res = await get(`/orgs/${org}/leaderboard`, { period: 'yearly', limit: 10 });
    const list = Array.isArray(res.data) ? res.data : [];
    let ranksOk = true;
    for (let i = 0; i < list.length; i++) {
      if (list[i].rank !== i + 1) ranksOk = false;
      if (Number(list[i].prs) < 0 || Number(list[i].score) < 0) ranksOk = false;
    }
    if (ranksOk) ok(`leaderboard ranks ${org}`, list.map((x) => `${x.rank}:${x.login}(prs=${x.prs})`).join(', '));
    else bad(`leaderboard ranks ${org}`, 'rank/score issue');
  }

  // 5) DB: PR events have required FKs
  console.log('\n=== DB integrity for PRs ===');
  const orphan = await pool.query(`
    SELECT COUNT(*)::int AS c FROM activity_events e
    LEFT JOIN repos r ON r.github_repo_id = e.repo_id
    WHERE e.event_type = 'pr' AND r.github_repo_id IS NULL
  `);
  if (orphan.rows[0].c === 0) ok('no orphan PR events');
  else bad('orphan PR events', String(orphan.rows[0].c));

  const nullUser = await pool.query(`
    SELECT COUNT(*)::int AS c FROM activity_events e
    LEFT JOIN github_users u ON u.id = e.user_id
    WHERE e.event_type = 'pr' AND u.id IS NULL
  `);
  if (nullUser.rows[0].c === 0) ok('all PR events have users');
  else bad('PR events missing users', String(nullUser.rows[0].c));

  console.log(`\nPASS=${pass} FAIL=${fail}`);
  await pool.end();
  process.exit(fail > 0 ? 1 : 0);
}

main().catch(async (e) => {
  console.error(e);
  try { await pool.end(); } catch (_) {}
  process.exit(1);
});
