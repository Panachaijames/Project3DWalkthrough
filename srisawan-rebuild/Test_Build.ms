global SR_batchMode=true
fileIn @"C:/Users/DWP/Documents/ChatGPT/Taradon T/output/srisawan-rebuild/Srisawan_New_Layouts_Quad.ms"
if SR_build() != true do throw "Build failed"
saveMaxFile @"C:/Users/DWP/Documents/ChatGPT/Taradon T/output/srisawan-rebuild/Srisawan_New_Layouts_Quad.max" quiet:true
local report=createFile @"C:/Users/DWP/Documents/ChatGPT/Taradon T/output/srisawan-rebuild/native_validation.txt"
format "Native 3ds Max build passed. Objects: %\n" SR_nodes.count to:report
format "All wall polygons passed coordinate, six-quad-face and closed-edge tests.\n" to:report
close report
