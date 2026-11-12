## Detailed Testing Commands
PowerShell Commands untuk Testing Backend:

### 1. Health Check
```bash
Invoke-RestMethod -Uri "http://localhost:5000/health" -Method GET
```

#### 2. Model Info
```bash
Invoke-RestMethod -Uri "http://localhost:5000/model_info" -Method GET
```

### 3. Test dengan CV Model (Real Detection)
```bash
$body = @{
    bounds = @{
        _southWest = @{
            lat = -6.875
            lng = 107.59
        }
        _northEast = @{
            lat = -6.870
            lng = 107.595
        }
    }
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:5000/process_region" -Method POST -Body $body -ContentType "application/json"
$response | ConvertTo-Json -Depth 10
```

### 4. Test Dummy Fallback
```bash
Invoke-RestMethod -Uri "http://localhost:5000/process_region_dummy" -Method POST -Body $body -ContentType "application/json"
```

### 5. Save response to file
```
$response | ConvertTo-Json -Depth 10 | Out-File -FilePath "response.json"
```
## Postman Collections:

Health Check
- Method: GET
URL: http://localhost:5000/health

Model Information
- Method: GET
URL: http://localhost:5000/model_info

CV Detection
- Method: POST
URL: http://localhost:5000/process_region

Dummy Detection
- Method: POST
URL: http://localhost:5000/process_region_dummy


Body (raw JSON):
```
json
{
  "bounds": {
    "_southWest": {"lat": -6.875, "lng": 107.59},
    "_northEast": {"lat": -6.870, "lng": 107.595}
  }
}
```