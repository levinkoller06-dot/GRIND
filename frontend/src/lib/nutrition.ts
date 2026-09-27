export type MealItem = {
  name: string;
  amount: string | null;
  kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
};

export type Meal = {
  id: string;
  eaten_at: string;
  meal_type: string;
  description: string | null;
  from_photo: boolean;
  meal_items: MealItem[];
};

export const MEAL_LABEL: Record<string, string> = {
  fruehstueck: "🥣 Frühstück",
  mittag: "🍝 Mittag",
  abend: "🍽️ Abend",
  snack: "🍎 Snack",
};

export function sum(items: MealItem[]) {
  return items.reduce(
    (t, i) => ({
      kcal: t.kcal + Number(i.kcal),
      protein_g: t.protein_g + Number(i.protein_g),
      carbs_g: t.carbs_g + Number(i.carbs_g),
      fat_g: t.fat_g + Number(i.fat_g),
    }),
    { kcal: 0, protein_g: 0, carbs_g: 0, fat_g: 0 },
  );
}

export const round = (n: number) => Math.round(n).toLocaleString("de-DE");
