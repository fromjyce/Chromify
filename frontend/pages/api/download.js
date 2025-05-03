import fs from 'fs';
import path from 'path';

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { path: filePath } = req.query;
  if (!filePath) {
    return res.status(400).json({ error: 'File path is required' });
  }

  try {
    const decodedPath = decodeURIComponent(filePath);
    if (!fs.existsSync(decodedPath)) {
      return res.status(404).json({ error: 'File not found' });
    }

    const fileStream = fs.createReadStream(decodedPath);
    const filename = path.basename(decodedPath);
    
    res.setHeader('Content-Disposition', `attachment; filename=${filename}`);
    fileStream.pipe(res);
  } catch (error) {
    console.error('Download error:', error);
    res.status(500).json({ error: error.message });
  }
}