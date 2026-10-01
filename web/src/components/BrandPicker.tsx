import { Select } from "./ui/Field";

interface Brand {
  id: number;
  name: string;
}

// Toolbar brand picker shared by Channels / Studio / Calendar / Insights.
export default function BrandPicker({
  brands,
  selectedId,
  onSelect,
}: {
  brands: Brand[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-[13px] text-mute">
      Brand
      <Select value={selectedId ?? ""} onChange={(e) => onSelect(Number(e.target.value))}>
        {brands.map((b) => (
          <option key={b.id} value={b.id}>
            {b.name}
          </option>
        ))}
      </Select>
    </label>
  );
}
