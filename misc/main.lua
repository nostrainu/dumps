if not game:IsLoaded() then game.Loaded:Wait() end

player.DevCameraOcclusionMode = "Invisicam"

player.Idled:Connect(function()
    virtual_user:CaptureController()
    virtual_user:ClickButton2(Vector2.new())
end)

local games = {
    [3840352284] = "volleyball_4.2",
}

local name = rawget(list, game.GameId) 
local file = ("list/%*/script.lua"):format(name):gsub(" ", "%%20")
if not name then return end

get_github_file(file)
