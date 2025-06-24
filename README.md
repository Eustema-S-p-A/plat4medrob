# Plat4MedRob
 
## Overview
 
**Plat4MedRob** is a modular platform for managing multimodal data in the field of robotic rehabilitation. It supports the ingestion, harmonization (into interoperable standards), and aggregation of clinical and device data. The platform enables advanced analytics functionalities for clinicians and researchers.
 
## Features
 
- **data-access-layer**:  
  Handles secure access to the underlying databases. It supports full CRUD operations and manages healthcare data formats such as **FHIR** and **DICOM**.
 
- **fhir-converter**:  
  Converts proprietary input data formats into standardized **FHIR** resources in JSON format, enabling data interoperability across systems.
 
- **data-analytics**:  
  Provides tools for generating reports and performing statistical analysis on harmonized datasets, facilitating clinical insights and decision support.
 
## Installation
 
The core of the platform is composed of three Dockerized modules:
 
1. **data-access-layer**  
2. **fhir-converter**  
3. **data-analytics**
 
To deploy the platform locally:
 
```bash
# Clone the repository
git clone https://github.com/Eustema-S-p-A/plat4medrob.git
cd plat4medrob
 
# Build and start the containers (example with Docker Compose)
docker compose up --build
```
 
> Note: Each module has its own Dockerfile and can be run individually or as part of an orchestrated stack.

## Contributing

Contributions are welcome!  
Feel free to open an issue for bug reports, feature requests, or general feedback.  
Pull requests are also encouraged for improvements, fixes, or new features.

## Contact

For questions or support, please use the [GitHub Issues](https://github.com/Eustema-S-p-A/plat4medrob/issues) section of the repository.


## Project and Funding

This platform has been developed as part of the **Fit4MedRob** initiative:  
🔗 [www.fit4medrob.it](https://www.fit4medrob.it/)

The project is funded by the **Italian Ministry of University and Research (MUR)** through the **National Complementary Plan (PNC)** of the **National Recovery and Resilience Plan (PNRR)**.
