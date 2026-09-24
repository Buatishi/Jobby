-- Chequeo de la migración 025: una persona autenticada no puede escribir sus filas por la API
-- REST de Supabase. Correrlo contra el proyecto de PRUEBAS (nunca producción): crea una
-- identidad ficticia, se hace pasar por ella como lo haría PostgREST e intenta cambiarse el
-- plan. Todo se deshace al final porque el bloque termina siempre con un error.
--
-- Resultado esperado: "RESULTADO: permiso denegado (...)".
-- Antes de la 025 respondía: "RESULTADO: la persona se cambió el plan a premium".

do $$
declare
  attacker constant uuid := '11111111-1111-4111-8111-111111111111';
  new_tier text;
begin
  insert into auth.users (id, email, aud, role)
  values (attacker, 'audit@example.invalid', 'authenticated', 'authenticated');
  -- Un trigger de auth.users crea la fila en public.users.
  execute 'set local role authenticated';
  perform set_config(
    'request.jwt.claims',
    json_build_object('sub', attacker, 'role', 'authenticated')::text,
    true
  );
  perform set_config('request.jwt.claim.sub', attacker::text, true);
  update public.users set tier = 'premium', subscription_status = 'active'
    where supabase_uid = attacker returning tier into new_tier;
  raise exception 'RESULTADO: la persona se cambió el plan a %', coalesce(new_tier, '(ninguna fila)');
exception
  when insufficient_privilege then
    raise exception 'RESULTADO: permiso denegado (%).', sqlerrm;
end $$;
