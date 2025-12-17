# Feature Identifier Web App

A py4web application for identifying outlined rectangular figures in images based on size and color consistency constraints.

## Features

- **Upload Images**: Accepts common formats (JPG, PNG, WebP).
- **Customizable Parameters**: Set min/max width and height, and color similarity threshold (Delta E).
- **Advanced Detection**:
  - Uses CIE76 Delta E for color comparison.
  - Validates outlines by checking color consistency with neighboring pixels along the bounding box.
  - Enforces exclusivity (non-overlapping figures).
- **Fast & Responsive**: Modern UI with Bootstrap 5, efficient numpy-based processing.

## Setup

### Prerequisites

- Python 3.8+
- `pip` or `uv`

### Installation

1. Clone the repository.
2. Install dependencies:

```bash
pip install -r requirements.txt
# OR with uv
uv pip install -r requirements.txt
```

### Running the App

To start the development server:

```bash
py4web run apps
```

Access the application at `http://127.0.0.1:8000/feature_site`.

## Algorithm Details

1. **Preprocessing**: Converts image to CIE Lab color space. Generates candidate bounding boxes using Canny edge detection and contour finding.
2. **Filtering**: Discards candidates outside the user-specified width/height ranges.
3. **Validation**:
   - Extracts pixels along the candidate's bounding box perimeter.
   - For each perimeter pixel, searches neighbors within ±10 pixels along the perimeter path.
   - A pixel is "supported" if a neighbor has a Delta E color difference $\le$ threshold.
   - Candidate is accepted if $\ge 80\%$ of perimeter pixels are supported.
4. **Exclusivity**:
   - Candidates are ranked by score (validation ratio).
   - The highest-scoring candidates are selected greedily.
   - Once a candidate is selected, its interior pixels are marked as occupied.
   - Subsequent candidates overlapping occupied regions are rejected.

## Usage Example

1. Open the web interface.
2. Upload an image containing outlined boxes (e.g., a hand-drawn diagram or shapes).
3. Set the expected size range (e.g., Min W: 50, Max W: 200).
4. Set Delta E threshold (default 2.3 is standard for "just noticeable difference", increase for noisier images).
5. Click "Run Detection".
6. View the overlay image and the JSON data.

## Testing

Run the unit tests:

```bash
python3 tests/test_algo.py
```
