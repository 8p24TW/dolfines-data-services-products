const PYTHON_SERVICE_URL = process.env.PYTHON_SERVICE_URL ?? "http://localhost:8000";

function isLocalPythonUrl(value: string) {
  return /localhost:8000|127\.0\.0\.1:8000/i.test(value);
}

export async function proxyToPythonService(path: string, formData: FormData) {
  if (process.env.NODE_ENV === "production" && isLocalPythonUrl(PYTHON_SERVICE_URL)) {
    throw new Error(
      "PYTHON_SERVICE_URL is still pointing to localhost. Set it to the public Railway analysis-service URL before using REVEAL online."
    );
  }

  const response = await fetch(`${PYTHON_SERVICE_URL}${path}`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Python service request failed with ${response.status}`);
  }

  return response;
}

export async function getFromPythonService(path: string, query: Record<string, string | number>) {
  if (process.env.NODE_ENV === "production" && isLocalPythonUrl(PYTHON_SERVICE_URL)) {
    throw new Error(
      "PYTHON_SERVICE_URL is still pointing to localhost. Set it to the public Railway analysis-service URL before using REVEAL online."
    );
  }

  const qs = new URLSearchParams(
    Object.entries(query).map(([k, v]) => [k, String(v)])
  ).toString();

  const response = await fetch(`${PYTHON_SERVICE_URL}${path}?${qs}`);

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Python service request failed with ${response.status}`);
  }

  return response;
}

export async function postJsonToPythonService(path: string, body: unknown) {
  if (process.env.NODE_ENV === "production" && isLocalPythonUrl(PYTHON_SERVICE_URL)) {
    throw new Error(
      "PYTHON_SERVICE_URL is still pointing to localhost. Set it to the public Railway analysis-service URL before using REVEAL online."
    );
  }

  const response = await fetch(`${PYTHON_SERVICE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Python service request failed with ${response.status}`);
  }

  return response;
}
