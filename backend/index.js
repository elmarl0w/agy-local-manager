const express = require('express');
const cors = require('cors');
const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

app.get('/api/status', (req, res) => {
  res.json({ status: 'CloudCore systems are operational', message: 'Welcome to the future of cloud computing.' });
});

app.listen(PORT, () => {
  console.log(`Backend running on port ${PORT}`);
});
