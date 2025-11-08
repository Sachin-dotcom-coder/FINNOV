import mongoose from 'mongoose';

const AnomalySchema = new mongoose.Schema(
  {
    id: { type: String, required: true },
    type: { type: String, required: true },
    priority: { type: String, enum: ['low', 'medium', 'high'], required: true },
    description: { type: String, required: true },
    details: { type: String, required: true },
    resolved: { type: Boolean, default: false },
  },
  { _id: false }
);

const InvoiceSchema = new mongoose.Schema(
  {
    id: { type: String, required: true, unique: true },
    fileName: { type: String, required: true },
    fileUrl: { type: String },
    filePath: { type: String },
    vendor: { type: String, required: true },
    amount: { type: Number, required: true },
    date: { type: String, required: true },
    status: { type: String, enum: ['pending', 'verified', 'flagged'], default: 'pending' },
    anomalies: { type: [AnomalySchema], default: [] },
    uploadedAt: { type: Date, default: Date.now },
  },
  { timestamps: true }
);

export default mongoose.model('Invoice', InvoiceSchema);