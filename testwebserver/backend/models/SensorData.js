const mongoose = require("mongoose");

const sensorSchema = new mongoose.Schema({
    sensor_name: String,
    detection_count: Number,
    timestamp: { type: Date, default: Date.now }
});

module.exports = mongoose.model("SensorData", sensorSchema);
