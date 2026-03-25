{
  "name": "smarterp-frontend",
  "version": "1.0.0",
  "private": true,
  "description": "SmartERP - Enterprise Resource Planning System Frontend",
  "dependencies": {
    "@reduxjs/toolkit": "^2.2.5",
    "axios": "^1.7.2",
    "chart.js": "^4.4.3",
    "date-fns": "^3.6.0",
    "react": "^18.3.1",
    "react-chartjs-2": "^5.2.0",
    "react-datepicker": "^6.9.0",
    "react-dom": "^18.3.1",
    "react-icons": "^5.2.1",
    "react-redux": "^9.1.2",
    "react-router-dom": "^6.23.1",
    "react-scripts": "5.0.1",
    "react-table": "^7.8.0",
    "react-toastify": "^10.0.5",
    "recharts": "^2.12.7"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.5",
    "@testing-library/react": "^15.0.7",
    "@testing-library/user-event": "^14.5.2",
    "eslint": "^8.57.0",
    "eslint-config-prettier": "^9.1.0",
    "prettier": "^3.3.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject",
    "lint": "eslint src/",
    "format": "prettier --write src/"
  },
  "proxy": "http://localhost:8000",
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}
