if not game:IsLoaded() then game.Loaded:Wait() end
local player = game.Players.LocalPlayer
local virtual_user = game:GetService("VirtualUser")

player.DevCameraOcclusionMode = "Invisicam"

player.Idled:Connect(function()
    virtual_user:CaptureController()
    virtual_user:ClickButton2(Vector2.new())
end)

local games = {
    [3840352284] = "volleyball_4.2",
}

local name = rawget(games, game.GameId) 
local file = ("games/%*/script.lua"):format(name):gsub(" ", "%%20")
if not name then return end
print(file)

get_github_file(file)
