
Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio 14
VisualStudioVersion = 14.0.25420.1
MinimumVisualStudioVersion = 10.0.40219.1
% for name, guid in projs:
Project("${sln_guid}") = "${name}", "${name}.vcxproj", "${guid}"
% endfor
EndProject
Global
	GlobalSection(SolutionConfigurationPlatforms) = preSolution
		% for proj_plat, sln_plat in plats:
		Debug|${sln_plat} = Debug|${sln_plat}
		% endfor
		% for plat in plats:
		Release|${sln_plat} = Release|${sln_plat}
		% endfor
	EndGlobalSection
	GlobalSection(ProjectConfigurationPlatforms) = postSolution
		% for name, guid in projs:
		% for proj_plat, sln_plat in plats:
		${guid}.Debug|${sln_plat}.ActiveCfg = Debug|${proj_plat}
		${guid}.Debug|${sln_plat}.Build.0 = Debug|${proj_plat}
		% endfor
		% for proj_plat, sln_plat in plats:
		${guid}.Release|${sln_plat}.ActiveCfg = Release|${proj_plat}
		${guid}.Release|${sln_plat}.Build.0 = Release|${proj_plat}
		% endfor
		% endfor
	EndGlobalSection
	GlobalSection(SolutionProperties) = preSolution
		HideSolutionNode = FALSE
	EndGlobalSection
EndGlobal
