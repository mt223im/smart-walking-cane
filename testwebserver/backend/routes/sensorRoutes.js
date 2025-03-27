const express = require("express");
const SensorData = require("../models/SensorData");
const router = express.Router();

// ✅ Store sensor data
router.post("/obstacle", async (req, res) => {
    const { sensor_name, detection_count } = req.body;
    if (!sensor_name || typeof detection_count !== "number") return res.status(400).send("Invalid data");

    await SensorData.create({ sensor_name, detection_count });
    res.json({ status: "success", sensor_name, detection_count });
});

// ✅ Retrieve data from the last hour
router.get("/sensor-data", async (req, res) => {
    const oneHourAgo = new Date();
    oneHourAgo.setHours(oneHourAgo.getHours() - 1);

    const data = await SensorData.aggregate([
        { $match: { timestamp: { $gte: oneHourAgo } } },
        { $group: { _id: "$sensor_name", totalDetections: { $sum: "$detection_count" }, lastDetected: { $max: "$timestamp" } } },
        { $sort: { "_id": 1 } }
    ]);

    res.json(data);
});

module.exports = router;
