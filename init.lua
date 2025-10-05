local http = minetest.request_http_api()
local endpoint = "http://127.0.0.1:8080/collect"  -- votre service

local function push(data_tbl)
  if not http then return end
  http.fetch({
    url = endpoint,
    method = "POST",
    extra_headers = { "Content-Type: application/json" },
    data = minetest.write_json(data_tbl),
    timeout = 2,
  }, function(res)
    if not res.succeeded then
      minetest.log("warning", "[collect] HTTP failed: "..(res.code or "nil"))
    end
  end)
end

-- Exemple: envoyer périodiquement la liste joueurs + positions
local acc = 0
minetest.register_globalstep(function(dtime)
  acc = acc + dtime
  if acc >= 5 then
    acc = 0
    local payload = {}
    for _, pl in ipairs(minetest.get_connected_players()) do
      local pos = pl:get_pos()
      table.insert(payload, {name=pl:get_player_name(), x=pos.x, y=pos.y, z=pos.z})
    end
    push({type="players_pos", data=payload, t=os.time()})
  end
end)

