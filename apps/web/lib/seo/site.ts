// Única fuente de la URL pública para metadatos, sitemap y datos estructurados.
// `public/robots.txt` es un archivo estático: si el dominio cambia hay que editarlo a mano.
export const SITE_URL = "https://jobbyweb.vercel.app";
export const SITE_NAME = "Jobby";
// Única dirección de contacto del proyecto: la usan términos, privacidad y `llms.txt` (este
// último es estático, así que su `Contact:` se edita a mano y un test lo compara con esta).
export const SITE_CONTACT_EMAIL = "developjobby@gmail.com";
// Perfiles públicos del proyecto para `sameAs`. Se suma otro solo si existe y es del proyecto:
// un perfil personal o inventado le diría a Google algo que el sitio no puede respaldar.
export const SITE_SAME_AS = ["https://github.com/Buatishi/Jobby"];
