export type Tab = {
  href: string;
  label: string;
  icon: string;
  description: string;
};

export const TABS: Tab[] = [
  { href: "/", label: "Start", icon: "🧠", description: "Tagesübersicht und Chat" },
  { href: "/kalender", label: "Kalender", icon: "📅", description: "Schule, Termine, Tests, Geburtstage" },
  { href: "/noten", label: "Noten", icon: "📊", description: "Fächer, Noten und Tests" },
  { href: "/gym", label: "Gym", icon: "💪", description: "Dein Trainingsplan" },
  { href: "/ernaehrung", label: "Ernährung", icon: "🥗", description: "Kalorien, Protein und was du noch essen solltest" },
  { href: "/mails", label: "Mails", icon: "📬", description: "Zusammenfassungen, Entwürfe, Pakete" },
  { href: "/freizeit", label: "Freizeit", icon: "🎮", description: "Gaming-News, Free Games, Watchlist" },
  { href: "/geld", label: "Geld", icon: "💰", description: "Taschengeld, Sparziele, Preis-Wächter" },
];

export const SETTINGS_TAB: Tab = {
  href: "/einstellungen",
  label: "Einstellungen",
  icon: "⚙️",
  description: "Profil, Google verbinden, Ziele",
};
