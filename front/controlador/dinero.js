// Convierte lo que escribe la persona ("12,50", "12.5", "7") en céntimos enteros.
// Se trabaja siempre en céntimos para evitar errores de redondeo con decimales.
// Devuelve null si el texto no es un importe válido.
export function eurosACentimos(texto) {
  const limpio = String(texto).trim().replace(/\s/g, "").replace(",", ".");
  if (!/^\d{1,9}(\.\d{1,2})?$/.test(limpio)) return null;
  const [euros, centimos = ""] = limpio.split(".");
  return Number(euros) * 100 + Number(centimos.padEnd(2, "0"));
}
