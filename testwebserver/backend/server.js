const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");
const path = require("path");

const app = express();
app.use(express.json());
app.use(cors());

// ✅ Connect to MongoDB
mongoose.connect("mongodb://localhost:27017/obstacleDB", {
    useNewUrlParser: true,
    useUnifiedTopology: true
})
    .then(() => console.log("✅ Connected to MongoDB"))
    .catch(err => console.error("❌ MongoDB Connection Error:", err));

// ✅ Define Sensor Schema
const sensorSchema = new mongoose.Schema({
    sensor_name: String,
    detection_count: Number,
    timestamp: { type: Date, default: Date.now }
});

const SensorData = mongoose.model("SensorData", sensorSchema);

// ✅ API: Receive Data from ESP32
app.post("/obstacle", async (req, res) => {
    const { sensor_name, detection_count } = req.body;
    if (!sensor_name || typeof detection_count !== "number") {
        return res.status(400).send("Invalid data");
    }

    await SensorData.create({ sensor_name, detection_count });
    res.json({ status: "success", sensor_name, detection_count });
});

// ✅ API: Get Last 1 Hour Data for Each Sensor
app.get("/sensor-data", async (req, res) => {
    const oneHourAgo = new Date();
    oneHourAgo.setHours(oneHourAgo.getHours() - 1);

    const data = await SensorData.aggregate([
        { $match: { timestamp: { $gte: oneHourAgo } } },
        { $group: { _id: "$sensor_name", totalDetections: { $sum: "$detection_count" }, lastDetected: { $max: "$timestamp" } } },
        { $sort: { "_id": 1 } }
    ]);

    res.json(data);
});

// ✅ Serve Frontend Files
app.use(express.static(path.join(__dirname, "frontend")));

app.get("/", (req, res) => {
    res.sendFile(path.join(__dirname, "frontend", "index.html"));
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🚀 Server running on: http://localhost:${PORT}/`));
