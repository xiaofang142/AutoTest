import express from "express";
import cors from "cors";

const app = express();
app.use(cors());
app.use(express.json({ limit: "50mb" }));

interface StepRequest {
  action: string;
  target: string;
  value?: string;
  screenshot?: string;
}

interface StepResponse {
  success: boolean;
  confidence: number;
  message: string;
  screenshot?: string;
}

app.post("/agent/execute", async (req, res) => {
  const { action, target, value }: StepRequest = req.body;

  try {
    console.log(`[Executor] action=${action} target=${target}`);

    // Mock execution - returns success for all steps
    const response: StepResponse = {
      success: true,
      confidence: 0.95,
      message: `Executed: ${action} on "${target}"`,
    };
    res.json(response);
  } catch (error: any) {
    res.status(500).json({
      success: false,
      confidence: 0,
      message: error.message,
    });
  }
});

app.get("/health", (_req, res) => {
  res.json({ status: "ok", version: "0.1.0" });
});

const PORT = parseInt(process.env.PORT || "3100", 10);
app.listen(PORT, () => {
  console.log(`AutoTest Web Executor running on port ${PORT}`);
});
