# dcp-tools

__Tools to manage and load data for custom [Data Commons](https://datacommons.org/)
instances__

[![GitHub Repo](https://img.shields.io/badge/GitHub-bblocks--datacommons--tools-181717?style=flat-square&labelColor=%23ddd&logo=github&color=%23555&logoColor=%23000)](https://github.com/ONEcampaign/bblocks-datacommons-tools)
[![GitHub License](https://img.shields.io/github/license/ONEcampaign/bblocks-datacommons-tools?style=flat-square&labelColor=%23ddd)](https://github.com/ONEcampaign/bblocks-datacommons-tools/blob/main/LICENSE)
[![PyPI - Version](https://img.shields.io/pypi/v/dcp-tools?style=flat-square&labelColor=%23ddd)](https://pypi.org/project/dcp-tools/)


The `dcp-tools` package simplifies the process of preparing and loading data to custom 
Data Commons instances. It provides utilities for building and editing configuration, metadata, and data files, 
and automating the data load pipeline.

[Data Commons](https://datacommons.org/) is a Google initiative that brings together public data from a
wide range of sources into a unified knowledge graph, making it easier to explore and analyze 
information across domains. Organisations can create custom instances of Data Commons to host their 
own datasets, integrate them into the graph, and build tailored tools on top of the platform.

Custom instances allow you to take advantage of core features such as natural language search and interactive 
visualisations, while combining your own data with everything available in the base Data Commons.

`dcp-tools` is designed to simplify and automate steps to build your custom instance—removing
much of the manual work involved in formatting and loading data, and helping you get your custom 
knowledge graph up and running quickly.


**Key features**

- Build and edit `config.json` files programmatically
- Generate MCF files from simple metadata
- Upload CSV, MCF, and config files to Google Cloud Storage
- Trigger the data load job
- Use as a Python module or from the command line

Ready to get started using `dcp-tools`?<br> 
**Read [Getting started ↗](./getting-started.md).**

Want to learn more about Data Commons? <br>
**Read the official 
[Custom Data Commons documentation ↗](https://docs.datacommons.org/custom_dc/index.html).**