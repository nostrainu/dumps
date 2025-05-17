if not game:IsLoaded() then game.Loaded:Wait() end

getgenv().get_github_file = function(file)
    local user, repo = "nostrainu", "dumps"
    local file = ("https://raw.githubusercontent.com/%*/%*/refs/heads/main/%*"):format(user, repo, file)
    return loadstring(game:HttpGet(file))()
end

get_github_file("global.lua")

player.DevCameraOcclusionMode = "Invisicam"

player.Idled:Connect(function()
    virtual_user:CaptureController()
    virtual_user:ClickButton2(Vector2.new())
end)

local list = {
    [3840352284] = "volleyball_4.2",
}

local name = rawget(list, game.GameId) 
local file = ("list/%*/script.lua"):format(name):gsub(" ", "%%20")
if not name then return end

getgenv().load_file = function(name, file)
    local file = ("list/%*/func/%*"):format(name, file):gsub(" ", "%%20")
    return get_github_file(file)
end

get_github_file(file)
