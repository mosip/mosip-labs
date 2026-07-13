/**
 * End-to-end API verification (run: node scripts/fullApiTest.js)
 */
require('dotenv').config();
const axios = require('axios');
const pool = require('../db/dbPool');
const { ensureLookupTables } = require('../db/initLookupTables');

const BASE = process.env.API_BASE_URL || 'http://localhost:3000';
const ORGS = ['mosip', 'inji'];
const PERIODS = ['daily', 'weekly', 'monthly', 'yearly'];

let passed = 0;
let failed = 0;
const failures = [];

async function test(name, fn) {
  try {
    await fn();
    passed += 1;
    console.log(`PASS  ${name}`);
  } catch (error) {
    failed += 1;
    const message = error.response
      ? `${error.response.status} ${JSON.stringify(error.response.data)}`
      : error.message;
    failures.push({ name, message });
    console.log(`FAIL  ${name}: ${message}`);
  }
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function main() {
  console.log('=== Lookup seeding from .env ===');
  const seed = await ensureLookupTables();
  assert(seed.roles.length > 0, 'USER_ROLES should parse at least one role from .env');
  assert(seed.orgs.length > 0, 'GITHUB_ORG should parse at least one org from .env');
  console.log(`Roles from .env: ${seed.roles.join(', ')}`);
  console.log(`Orgs from .env: ${seed.orgs.join(', ')}`);

  console.log('\n=== API tests ===');

  await test('GET / health', async () => {
    const { data, status } = await axios.get(`${BASE}/`);
    assert(status === 200, 'expected 200');
    assert(data.endpoints, 'expected endpoints map');
  });

  await test('GET /user-roles matches .env', async () => {
    const { data } = await axios.get(`${BASE}/user-roles`);
    assert(Array.isArray(data) && data.length > 0, 'expected role array');
    for (const role of seed.roles) {
      assert(
        data.some((row) => row.name === role),
        `missing role from .env: ${role}`
      );
    }
  });

  await test('GET /organizations matches .env', async () => {
    const { data } = await axios.get(`${BASE}/organizations`);
    assert(Array.isArray(data) && data.length > 0, 'expected org array');
    for (const slug of seed.orgs) {
      assert(
        data.some((row) => row.slug === slug),
        `missing org from .env: ${slug}`
      );
    }
  });

  for (const org of ORGS) {
    for (const period of PERIODS) {
      await test(`GET /orgs/${org}/summary?period=${period}`, async () => {
        const { data, status } = await axios.get(`${BASE}/orgs/${org}/summary`, {
          params: { period },
        });
        assert(status === 200, 'expected 200');
        assert(data && typeof data === 'object', 'expected summary object');
      });

      await test(`GET /orgs/${org}/activity?period=${period}`, async () => {
        const { data, status } = await axios.get(`${BASE}/orgs/${org}/activity`, {
          params: { period },
        });
        assert(status === 200, 'expected 200');
        assert(Array.isArray(data.labels), 'expected labels array');
      });

      await test(`GET /orgs/${org}/leaderboard?period=${period}`, async () => {
        const { data, status } = await axios.get(`${BASE}/orgs/${org}/leaderboard`, {
          params: { period, limit: 5 },
        });
        assert(status === 200, 'expected 200');
        assert(Array.isArray(data.leaderboard), 'expected leaderboard array');
      });

      await test(`GET /orgs/${org}/users?period=${period}`, async () => {
        const { data, status } = await axios.get(`${BASE}/orgs/${org}/users`, {
          params: { period, page: 1, limit: 5 },
        });
        assert(status === 200, 'expected 200');
        assert(Array.isArray(data.users), 'expected users array');
      });
    }

    await test(`GET /orgs/${org}/summary invalid role returns 400`, async () => {
      try {
        await axios.get(`${BASE}/orgs/${org}/summary`, {
          params: { period: 'weekly', role: 'NotARealRole' },
        });
        throw new Error('expected 400');
      } catch (error) {
        assert(error.response?.status === 400, 'expected 400 for invalid role');
      }
    });

    await test(`GET /orgs/${org}/summary trimmed role filter`, async () => {
      const role = seed.roles[0];
      const a = await axios.get(`${BASE}/orgs/${org}/summary`, {
        params: { period: 'monthly', role: ` ${role} ` },
      });
      const b = await axios.get(`${BASE}/orgs/${org}/summary`, {
        params: { period: 'monthly', role },
      });
      assert(JSON.stringify(a.data) === JSON.stringify(b.data), 'trimmed role should match');
    });
  }

  const sampleUser = await pool.query(
  `
      SELECT u.login
      FROM github_users u
      JOIN activity_events e ON e.user_id = u.id
      JOIN repos r ON r.github_repo_id = e.repo_id
      WHERE LOWER(r.owner) = 'mosip'
      LIMIT 1
    `
  );

  if (sampleUser.rowCount > 0) {
    const login = sampleUser.rows[0].login;
    await test(`GET /orgs/mosip/users/${login}`, async () => {
      const { data, status } = await axios.get(`${BASE}/orgs/mosip/users/${login}`, {
        params: { period: 'monthly' },
      });
      assert(status === 200, 'expected 200');
      assert(data.user?.login === login, 'expected user login');
    });
  } else {
    console.log('SKIP  user details test (no activity users in DB)');
  }

  await test('POST /admin/users/role rejects non-string role', async () => {
    try {
      await axios.post(`${BASE}/admin/users/role`, {
        login: 'test-user',
        role: 123,
        organization: 'mosip',
      });
      throw new Error('expected 400');
    } catch (error) {
      assert(error.response?.status === 400, 'expected 400');
    }
  });

  await test('POST /admin/users/role rejects invalid role', async () => {
    try {
      await axios.post(`${BASE}/admin/users/role`, {
        login: 'test-user',
        role: 'FakeRole',
        organization: 'mosip',
      });
      throw new Error('expected 400');
    } catch (error) {
      assert(error.response?.status === 400, 'expected 400');
    }
  });

  const assignableLogin = sampleUser.rowCount > 0 ? sampleUser.rows[0].login : null;
  if (assignableLogin) {
    const role = seed.roles[0];
    await test(`POST /admin/users/role assign ${role} to ${assignableLogin}`, async () => {
      const { data, status } = await axios.post(`${BASE}/admin/users/role`, {
        login: assignableLogin,
        role,
        organization: 'mosip',
      });
      assert(status === 200, 'expected 200');
      assert(data.user?.role === role, 'expected assigned role in response');
    });

    await test(`GET /admin/users/${assignableLogin}/role`, async () => {
      const { data, status } = await axios.get(`${BASE}/admin/users/${assignableLogin}/role`);
      assert(status === 200, 'expected 200');
      assert(data.user?.role === seed.roles[0], 'expected stored role');
    });
  } else {
    console.log('SKIP  role assignment tests (no users in DB)');
  }

  console.log('\n=== Summary ===');
  console.log(`Passed: ${passed}`);
  console.log(`Failed: ${failed}`);
  if (failures.length > 0) {
    console.log('\nFailures:');
    for (const item of failures) {
      console.log(`- ${item.name}: ${item.message}`);
    }
    process.exitCode = 1;
  }
}

main()
  .catch((error) => {
    console.error('Test runner error:', error);
    process.exitCode = 1;
  })
  .finally(async () => {
    try {
      await pool.end();
    } catch {
      // ignore
    }
  });
