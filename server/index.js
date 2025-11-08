import express from 'express';
import cors from 'cors';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import morgan from 'morgan';
import dotenv from 'dotenv';
import mongoose from 'mongoose';
import { customAlphabet } from 'nanoid';
import Invoice from './models/Invoice.js';

dotenv.config();
const nanoid = customAlphabet('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', 8);
const app = express();

// Ensure uploads directory exists
const uploadsDir = path.resolve(process.cwd(), 'server', 'uploads');
fs.mkdirSync(uploadsDir, { recursive: true });

const storage = multer.diskStorage({
  destination: function (_req, _file, cb) {
    cb(null, uploadsDir);
  },
  filename: function (_req, file, cb) {
    const ts = Date.now();
    const safe = file.originalname.replace(/[^a-zA-Z0-9._-]/g, '_');
    cb(null, `${ts}_${safe}`);
  },
});
const upload = multer({ storage });

app.use(cors());
app.use(express.json());
app.use(morgan('dev'));
app.use('/uploads', express.static(uploadsDir));

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017/finnov';
await mongoose.connect(MONGODB_URI);

app.get('/api/health', (_req, res) => res.json({ ok: true }));

function runExtractionLogic(fileName) {
  // Basic, deterministic extraction from filename pattern e.g. vendor-1234.pdf
  const base = fileName.split('.')[0];
  const vendor = base.replace(/[_-]?\d+.*/g, '').slice(0, 24) || 'Unknown Vendor';
  const m = base.match(/(\d+)(?:\D|$)/);
  const amount = m ? Math.max(100, parseInt(m[1], 10)) : Math.floor(Math.random() * 9000) + 1000;
  const anomalies = [];
  if (/mismatch|error|diff/i.test(fileName)) {
    anomalies.push({
      id: `anom-${Date.now()}-1`,
      type: 'amount_mismatch',
      priority: 'high',
      description: 'Amount Mismatch',
      details: "Invoice total doesn't match purchase order amount",
      resolved: false,
    });
  }
  if (/late|overdue/i.test(fileName)) {
    anomalies.push({
      id: `anom-${Date.now()}-2`,
      type: 'date_validation',
      priority: 'medium',
      description: 'Date Validation',
      details: 'Invoice date seems older than expected',
      resolved: false,
    });
  }
  return { vendor, amount, anomalies };
}

app.post('/api/invoices/analyze', upload.array('files'), async (req, res) => {
  try {
    const files = req.files || [];

    const saved = await Promise.all(
      files.map(async (f) => {
        const id = `INV-${new Date().getFullYear()}-${nanoid()}`;
        const { vendor, amount, anomalies } = runExtractionLogic(f.originalname);
        const fileUrl = `/uploads/${path.basename(f.path)}`;

        const doc = await Invoice.create({
          id,
          fileName: f.originalname,
          fileUrl,
          filePath: f.path,
          vendor,
          amount,
          date: new Date().toISOString().split('T')[0],
          status: 'pending',
          anomalies,
          uploadedAt: new Date(),
        });
        return doc.toObject();
      })
    );

    res.json({ invoices: saved });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: 'Failed to analyze invoices' });
  }
});

app.get('/api/invoices', async (_req, res) => {
  const items = await Invoice.find().sort({ createdAt: -1 }).lean();
  res.json({ invoices: items });
});

app.get('/api/invoices/:id', async (req, res) => {
  const item = await Invoice.findOne({ id: req.params.id }).lean();
  if (!item) return res.status(404).json({ error: 'Not found' });
  res.json({ invoice: item });
});

// Update anomaly resolution and recompute invoice status
app.patch('/api/invoices/:id/anomalies/:anomalyId', async (req, res) => {
  const { id, anomalyId } = req.params;
  const { resolved } = req.body || {};
  const doc = await Invoice.findOne({ id });
  if (!doc) return res.status(404).json({ error: 'Not found' });
  const idx = doc.anomalies.findIndex(a => a.id === anomalyId);
  if (idx === -1) return res.status(404).json({ error: 'Anomaly not found' });
  doc.anomalies[idx].resolved = Boolean(resolved);
  const allResolved = doc.anomalies.every(a => a.resolved);
  doc.status = allResolved ? 'verified' : 'pending';
  await doc.save();
  return res.json({ invoice: doc.toObject() });
});

// Download original file with correct filename
app.get('/api/invoices/:id/download', async (req, res) => {
  const item = await Invoice.findOne({ id: req.params.id }).lean();
  if (!item || !item.filePath) return res.status(404).json({ error: 'File not found' });
  try {
    return res.download(item.filePath, item.fileName);
  } catch (e) {
    console.error(e);
    return res.status(500).json({ error: 'Failed to download file' });
  }
});

const PORT = process.env.PORT || 5050;
app.listen(PORT, () => {
  console.log(`Server listening on http://localhost:${PORT}`);
});
