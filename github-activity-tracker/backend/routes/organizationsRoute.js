const express = require('express');
const router = express.Router();
const { getAllOrganizations } = require('../services/organizationsService');

router.get('/organizations', async (req, res) => {
  try {
    const organizations = await getAllOrganizations();
    return res.status(200).json(organizations);
  } catch (error) {
    console.error('Error fetching organizations:', error);
    return res.status(500).json({ error: 'Failed to fetch organizations' });
  }
});

module.exports = router;
