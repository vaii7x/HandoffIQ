import express, { Request, Response } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { authService } from './services/authService';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(cors());

app.post('/api/auth/register', async (req: Request, res: Response) => {
  try {
    const { email, password } = req.body;
    const result = await authService.register(email, password);
    
    if (!result.success) {
      return res.status(400).json({ error: result.error });
    }

    return res.status(201).json({ message: 'User registered successfully.' });
  } catch (error) {
    return res.status(500).json({ error: 'Internal server error.' });
  }
});

app.post('/api/auth/login', async (req: Request, res: Response) => {
  try {
    const { email, password } = req.body;
    const result = await authService.login(email, password);

    if (!result.success) {
      return res.status(401).json({ error: result.error });
    }

    return res.status(200).json({ message: 'Login successful.', token: result.token });
  } catch (error) {
    return res.status(500).json({ error: 'Internal server error.' });
  }
});

app.get('/health', (_req: Request, res: Response) => {
  res.status(200).json({ status: 'OK', timestamp: new Date().toISOString() });
});

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});

export default app;
