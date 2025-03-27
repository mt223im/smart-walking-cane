async function fetchSensorData() {
    try {
        let response = await fetch("/sensor-data");
        if (!response.ok) {
            throw new Error("Failed to fetch data");
        }

        let data = await response.json();
        let tableBody = document.getElementById("sensorTable");
        tableBody.innerHTML = ""; // Clear previous data

        if (data.length === 0) {
            tableBody.innerHTML = "<tr><td colspan='3'>No data available</td></tr>";
            return;
        }

        data.forEach(sensor => {
            let row = `<tr>
                <td>${sensor._id}</td>
                <td>${sensor.totalDetections}</td>
                <td>${new Date(sensor.lastDetected).toLocaleTimeString()}</td>
            </tr>`;
            tableBody.innerHTML += row;
        });
    } catch (error) {
        console.error("Error fetching data:", error);
    }
}

// Fetch data every 10 seconds
setInterval(fetchSensorData, 10000);
fetchSensorData();
