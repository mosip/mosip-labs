const express = require('express');
const router = express.Router();
const { getAllUserRoles } = require('../services/userRolesService');

router.get('/user-roles', async (req, res) => {
  try {
    const roles = await getAllUserRoles();
    return res.status(200).json(roles);
  } catch (error) {
    console.error('Error fetching user roles:', error);
    return res.status(500).json({ error: 'Failed to fetch user roles' });
  }
});

module.exports = router;
