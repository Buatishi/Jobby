export type GreetingKey = "app.goodMorning" | "app.goodAfternoon" | "app.goodNight";

// Mañana hasta las 11:59, tarde hasta las 19:59 y noche desde las 20.
export function greetingKeyForHour(hour: number): GreetingKey {
  if (hour < 12) {
    return "app.goodMorning";
  }

  return hour < 20 ? "app.goodAfternoon" : "app.goodNight";
}

// Usa la zona horaria de donde corre el código: en el navegador es la de la persona.
export function formatToday(now: Date, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    weekday: "long",
    day: "numeric",
    month: "long"
  }).format(now);
}
