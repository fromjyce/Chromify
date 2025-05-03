import { IncomingForm } from 'formidable';
import { createReadStream } from 'fs';
import FormData from 'form-data';
import axios from 'axios';

export const config = {
  api: {
    bodyParser: false,
  },
};

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const form = new IncomingForm();
    const [fields, files] = await new Promise((resolve, reject) => {
      form.parse(req, (err, fields, files) => {
        if (err) return reject(err);
        resolve([fields, files]);
      });
    });

    if (!files?.file) {
      return res.status(400).json({ error: 'No file provided' });
    }

    const file = Array.isArray(files.file) ? files.file[0] : files.file;
    
    if (!file?.filepath) {
      return res.status(400).json({ error: 'Invalid file upload' });
    }

    const formData = new FormData();
    formData.append('file', createReadStream(file.filepath), {
      filename: file.originalFilename || file.newFilename,
      knownLength: file.size
    });

    const response = await axios.post('http://localhost:8000/upload', formData, {
      headers: {
        ...formData.getHeaders(),
      },
      maxBodyLength: Infinity,
    });

    res.status(200).json(response.data);
  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({ 
      error: 'Upload failed',
      details: error.message,
      stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
    });
  }
}