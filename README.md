# Environmental impacts of continuous integration

Continuous integration (CI) is used across the world to build, test, and deploy software. But as [human-induced climate change is causing dangerous and widespread disruption in nature and affecting the lives of billions of people around the world](https://www.ipcc.ch/report/ar6/wg2/resources/press/press-release/), what impact does running all this CI have on our planet?

Since I couldn't find any good answers to that question, this repository is an attempt to find out.

## Methodology
The general idea is to scrape the GitHub API for the durations and operating systems of GitHub Actions jobs.
From this information, we can guesstimate the the power consumed and associated emissions using the assumptions below.

### Carbon emission assumptions
Data is taken from [v2.1 of the Green Algorithms datasets](https://github.com/GreenAlgorithms/green-algorithms-tool/tree/master/data/v2.1).

- All cores are being utilised 100% throughout runs.
- The power usage effectiveness is 1.125. This is a multiplier added on top of the CPU power consumption to account for the power needed to run a datacenter (e.g. cooling, lighting)
- The carbon intensity is 357.32 gCO2e/kWh. This is an average of carbon intensity for all [the datacenters that host GitHub actions runners](https://github.community/t/github-runners-physical-location/162436/2):
    - East US (eastus) in US-VA (354.25 gCO2e/kWh)
    - East US 2 (eastus2) in US-VA (354.25 gCO2e/kWh)
    - West US 2 (westus2) in US-WA (95.34 gCO2e/kWh)
    - Central US (centralus) in US-IA (513.78 gCO2e/kWh)
    - South Central US (southcentralus) in US-TX (468.98 gCO2e/kWh)

## Results

## Useful links

- [Argos: Measure The Carbon Footprint Of Software, Improve Developer Practices](https://marmelab.com/blog/2020/11/26/argos-sustainable-development.html)
- [energyusage Python packge](https://pypi.org/project/energyusage/#description)
- [The Green Algorithms calculator](https://www.green-algorithms.org/)
- [The Shift Project](https://theshiftproject.org/lean-ict/)
