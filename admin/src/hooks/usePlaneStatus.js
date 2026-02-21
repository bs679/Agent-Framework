import { useState, useEffect, useCallback, useRef } from "react";

const POLL_INTERVAL = 30_000;

export default function usePlaneStatus() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastFetched, setLastFetched] = useState(null);
  const intervalRef = useRef(null);

  const fetchPlane = useCallback(async () => {
    try {
      const token = localStorage.getItem("admin_token") || "";
      const res = await fetch("/api/v1/admin/plane", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 403) {
        setError("Access denied. Admin role required.");
        setLoading(false);
        return;
      }
      if (!res.ok) {
        setError(`API error: ${res.status}`);
        setLoading(false);
        return;
      }
      const json = await res.json();
      setData(json);
      setError(null);
      setLastFetched(new Date());
    } catch (err) {
      setError("Unable to reach API");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPlane();
    intervalRef.current = setInterval(fetchPlane, POLL_INTERVAL);
    return () => clearInterval(intervalRef.current);
  }, [fetchPlane]);

  return { data, error, loading, lastFetched, refresh: fetchPlane };
}
