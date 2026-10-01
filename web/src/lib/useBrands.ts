import { useEffect, useState } from "react";
import { api, type Brand } from "./api";

// Shared brand list loader + a small global selection so pages agree on the current brand.
let _selectedId: number | null = null;

export function useBrands() {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(_selectedId);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = async () => {
    setLoading(true);
    try {
      const data = await api.listBrands();
      setBrands(data);
      if (data.length && (selectedId == null || !data.some((b) => b.id === selectedId))) {
        _selectedId = data[0].id;
        setSelectedId(data[0].id);
      }
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const select = (id: number) => {
    _selectedId = id;
    setSelectedId(id);
  };

  return { brands, selectedId, select, reload, loading, error };
}