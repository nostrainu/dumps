if game.PlaceId ~= 3840352284 then return end

local repo = "https://raw.githubusercontent.com/deividcomsono/Obsidian/main/"
local Library = loadstring(game:HttpGet(repo .. "Library.lua"))()
local ThemeManager = loadstring(game:HttpGet(repo .. "addons/ThemeManager.lua"))()

local http_service = game:GetService("HttpService")
local folder = "hikochairs"
local path = folder .. "/hikoconfig.json"

getgenv().config = {}

local function loadConfig()
    if isfile(path) then
        getgenv().config = http_service:JSONDecode(readfile(path))
    else
        getgenv().config = {}
    end
end

local function saveConfig()
    if not isfolder(folder) then makefolder(folder) end
    writefile(path, http_service:JSONEncode(getgenv().config))
end

loadConfig()
local defaults = {}
for key, default in pairs(defaults) do
    getgenv()[key] = getgenv().config[key] ~= nil and getgenv().config[key] or default
end

Library.ForceCheckbox = false
Library.ShowToggleFrameInKeybinds = true

local Window = Library:CreateWindow({
    Title = "Oppslead",
    Footer = "VB4.2 Shitter",
    MobileButtonsSide = "Left",
    NotifySide = "Right",
    Center = true,
    Size = Library.IsMobile and UDim2.fromOffset(150, 200) or UDim2.fromOffset(350, 400),
    ShowCustomCursor = false,
})

local Tabs = {
    Main = Window:AddTab("Main", "user"),
    ["UI Settings"] = Window:AddTab("UI Settings", "settings"),
}

local LeftGroupBox = Tabs.Main:AddLeftGroupbox("Infinite Stam")

LeftGroupBox:AddButton({
    Text = "Modify Functions",
    Func = function()
        local success, err = pcall(function()
            if not debug.getconstants or not debug.setconstant then
                Library:Notify({
                    Title = "Error",
                    Description = "Get better executor bro, this aint working on your sht",
                    Time = 5
                })
                return
            end

            local foundFuncs = {}

            local gc = getgc and getgc(true) or {}
            local targetConstant = 0.6

            for _, item in pairs(gc) do
                if type(item) == "function" and (not is_synapsefunction or not is_synapsefunction(item)) then
                    local ok, constants = pcall(debug.getconstants, item)
                    if ok and type(constants) == "table" then
                        for _, constant in pairs(constants) do
                            if constant == targetConstant then
                                table.insert(foundFuncs, item)
                                if constants[8] ~= nil then
                                    pcall(function() debug.setconstant(item, 8, math.huge) end)
                                end
                                if constants[10] ~= nil then
                                    pcall(function() debug.setconstant(item, 10, math.huge) end)
                                end
                                break
                            end
                        end
                    end
                end
            end

            Library:Notify({
                Title = "Functions Modified",
                Description = "Just shitted on this game.",
                Time = 5
            })
        end)
        if not success then
            warn("shit", err)
        end
    end
})

local MenuGroup = Tabs["UI Settings"]:AddLeftGroupbox("Menu")

MenuGroup:AddDropdown("NotificationSide", {
    Values = { "Left", "Right" },
    Default = "Right",
    Text = "Notification Side",
    Callback = function(Value)
        Library:SetNotifySide(Value)
    end,
})

MenuGroup:AddDropdown("DPIDropdown", {
    Values = { "50%", "75%", "100%", "125%", "150%", "175%", "200%" },
    Default = "100%",
    Text = "DPI Scale",
    Callback = function(Value)
        Value = Value:gsub("%%", "")
        local DPI = tonumber(Value)
        Library:SetDPIScale(DPI)
    end,
})

MenuGroup:AddDivider()
MenuGroup:AddLabel("Menu bind")
    :AddKeyPicker("MenuKeybind", { Default = "LeftControl", NoUI = true, Text = "Menu keybind" })

MenuGroup:AddButton("Unload", function()
    Library:Unload()
end)

Library.ToggleKeybind = Library.Options.MenuKeybind

ThemeManager:SetLibrary(Library)
ThemeManager:SetFolder("hikochairs")
ThemeManager:ApplyToTab(Tabs["UI Settings"])
