import waveassist

# Initialize WaveAssist SDK (no check_credits flag in the starting node)
waveassist.init()

# Credits estimate for GitFlow
CREDITS_NEEDED_FOR_RUN = 0.3

print("GitFlow: Starting credits check and initialization...")

# Check credits and notify if insufficient
success = waveassist.check_credits_and_notify(
    required_credits=CREDITS_NEEDED_FOR_RUN,
    assistant_name="GitFlow",
)

if not success:
    display_output = {
        "html_content": "<p>Credits were not available, the GitFlow run was skipped.</p>",
    }
    waveassist.store_data("display_output", display_output, run_based=True, data_type="json")
    raise Exception("Credits were not available, the GitFlow run was skipped.")

# Validate required inputs
project_name = waveassist.fetch_data("project_name", default="")
if not project_name or not str(project_name).strip():
    display_output = {
        "html_content": "<p>Project name is required but was not provided.</p>",
    }
    waveassist.store_data("display_output", display_output, run_based=True, data_type="json")
    raise Exception("Project name is required but was not provided.")

# Validate GitHub integration
github_access_token = waveassist.fetch_data("github_access_token", default="")
github_selected_resources = waveassist.fetch_data("github_selected_resources", default=[])

if not github_access_token:
    display_output = {
        "html_content": "<p>GitHub access token is required. Please connect your GitHub account.</p>",
    }
    waveassist.store_data("display_output", display_output, run_based=True, data_type="json")
    raise Exception("GitHub access token is required.")

if not isinstance(github_selected_resources, list) or len(github_selected_resources) == 0:
    display_output = {
        "html_content": "<p>No GitHub repositories selected. Please select at least one repository to track.</p>",
    }
    waveassist.store_data("display_output", display_output, run_based=True, data_type="json")
    raise Exception("No GitHub repositories selected.")

print(f"GitFlow: Initialized for project '{str(project_name).strip()}'")
print(f"GitFlow: Tracking {len(github_selected_resources)} repositories")
print("GitFlow: Credits check complete and initialization finished.")

