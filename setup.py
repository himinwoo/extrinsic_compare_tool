from setuptools import find_packages, setup


setup(
    name="extrinsic-compare",
    version="0.1.0",
    description="Small CLI tools for comparing radar-lidar extrinsic candidates.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
    package_dir={"": "src"},
    packages=find_packages("src"),
    install_requires=[
        "numpy>=1.21",
    ],
    entry_points={
        "console_scripts": [
            "extrinsic-compare=extrinsic_compare.cli:main",
            "ecmp=extrinsic_compare.cli:main",
        ],
    },
)
