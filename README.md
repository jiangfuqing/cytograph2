
# cytograph

## Installation

The following instructions should work for Linux and Mac (unfortunately, we have no 
experience with Windows).

1. [Install Anaconda](https://www.continuum.io/downloads), Python 3.7 version

2. Install [loompy](http://loompy.org)

3. Install `cytograph`:

```
git clone https://github.com/linnarsson-lab/cytograph2.git
cd cytograph2
pip install -e .
```

## Creating a build

An analysis in cytograph is called a "build" and is driven by configurations (settings, such as parameters to the algorithms) and punchcards (text files that define how samples are combined in the analysis). To create a build, you must first create a
*build folder* with the proper config and punchcards, and then execute the build. 

### Preparations

1. Prepare your input samples using [velocyto](http://velocyto.org) and place them in a folder. Below, the full path to this folder will be called `{samples}`. Each sample file should be named `{SampleID}.loom`. For example, `lung23.loom` is a sample with `SampleID` equal to `lung23`.

2. Prepare auto-annotations in a folder (we'll call its full path `{auto-annotations}`). For example, you can start with `Human` or `Mouse` from the [auto-annotation-md](https://github.com/linnarsson-lab/auto-annotation-md) repository.

3. Optionally create a metadata file (we'll call its full path `{metadata}`). The file should be semicolon-delimited with one header row, and one column heading should be `SampleID`. For each sample included in the build, the SampleID is matched against this column, and the corresponding row of metadata is added to the sample. For example, if the SampleID is `lung23`, then the metadata row where the `SampleID` column has value `lung23` is used. For each column, an attribute is added to the file with name equal to the column heading, and value equal to the value in the corresponding row. 

4. Optionally create a settings file `.cytograph` in your home directory, with content like this:

```
paths:
  samples: "{samples}"
  autoannotation: "{auto-annotation}"
  metadata: "{metadata}"
```

For example:

```
paths:
  samples: "/proj/loom"
  autoannotation: "/home/sten/proj/auto-annotation/Human"
  metadata: "/home/sten/proj/samples_csv.txt"
```

### Setting up the build folder

1. Create a build folder (full path `{build}`), and in this folder create a subfolder `punchcards`. Check out the [punchcards](https://github.com/linnarsson-lab/punchcards) repository for examples of punchcards.

2. Optionally create a file in the build folder called `config.yaml`, with content similar to the global config file (`~/.cytograph`). Any setting given in the build-specific config file will override the corresponding setting in the global config. For example, to use a different auto-annotation for a build, `config.yaml` would be give like so:

```
paths:
  autoannotation: "/home/sten/proj/auto-annotation/Mouse"
```

3. Create a root punchcard defintion named `Root.yaml` in the `punchcards` subfolder, with the following content:

```
MySamples:
    include: [10X121_1, 10X122_2]
```

Here, `MySamples` is the name that you give to a collection of samples, called a *Punchcard subset*. The samples are listes in brackets using their SampleIDs. Cytograph will collect the samples by reading from `{samples}/10X121_1.loom` and `{samples}/10X122_2.loom`
and will create an output file called `MySamples.loom`. Note that you can define multiple subsets, which you can then analyze separately.

Your build folder should look now like this:

```
/punchcards
    Root.yaml  # root punchcard, which defines the samples to include in the build
config.yaml    # optional build-specific config
```

### Running the pipeline

Run the following command from the terminal:

```
$ cytograph --build-location {build} process MySamples
```

This tells cytograph to process the Punchcard subset `MySamples`, which we defined in `Root.yaml`. Cytograph will run through a standard set of algorithms (pooling the samples, removing doublets,
Poisson pooling, matrix factorization, manifold learning, clustering, and embedding). Several outputs will be produced, resulting in the following build folder:

```
/data
    MySamples.loom
    MySamples.agg.loom
/exported
    MySamples/
        .
        . Lots of plots
        .
/punchcards
    Root.yaml  # root punchcard, which defines the samples to include in the build
config.yaml    # optional build-specific config

```


### Splitting the data, and running a complete build

The commmand in the previous section runs a single punchcard subset (`MySamples`). In this section, we will learn how to sequentially split the analysis using auto-annotation, and
how to run a complete set of punchcards (a "deck") both locally and on a compute cluster.

Start by adding another punchcard, named `MySamples.yaml`, with the following content:

```
Microglia:
  include: [M-MGL]
Erythrocytes:
  include: [M-ERY]
Endothelial:
  include: [M-ENDO]
Fibroblast:
  include: [M-VLMC]
Floorplate:
  include: [P-FPE, P-FPL]
NeuralCrest:
  include: [NE-SCHWL]
RadialGlia:
  include: [S-CC]
Neuronal:
  include: []
```

The name of the punchcard (`MySamples.yaml`) indicates that this is a punchcard that takes its cells from the `MySamples` subset in `Root.yaml`. The name is case-sensitive.

Each section in the punchcard (e.g. `Microglia`) defines a new subset. However, this time we are not getting cells from raw samples, but rather selecting cells using auto-annotation,
and taking them from the parent punchcard (i.e. `MySamples.loom`). The statement `include: [P-FPE, P-FPL]` means *include all clusters that were annotated with `P-FPE` or `P-FPL`*. 
Note that the subsets are evaluated in order, and cells are assigned to the first subset that matches. The empty subset `[]` is special; it means 
*include all cells that have not yet been included*. In the case above, any cell that was not assigned to any of the previous
subsets, is assigned to `Neuronal`.


#### Processing the new subsets

Now we have two punchcards, defining nine subsets (`MySamples` in `Root.yaml`, and `Microglia`, ...., `Neuronal` in `MySamples.yaml`). Assuming you have already processed `MySamples` as above, you can now do:

```
cytograph process MySamples_Microglia
```

(Note: if you run this command in the build folder, you can omit the `--build-location` parameter as we did here.)

Each subset is designated by its "long name", which is the sequence of punchcards you have to go through to get to it (but 
omitting `Root`). If you had defined another punchcard `Microglia.yaml`, with another subset `ActivatedMicroglia`, then the long name of that subset would be `MySamples_Microglia_ActivatedMicroglia`.

#### Running a complete build automatically

It gets tedious to run all these subsets one by one using `cytograph process {subset}`. Cytograph therefore has a `build`
command that automates the process of figuring out what all the punchcards are, and how the subsets defined in them depend on each other:

```
cytograph build --engine local
```

Cytograph computes an execution graph based on the punchcard dependencies, sorts it so that dependencies come before the
subsets that depends on them, and then runs `cytograph process` on them sequentially.


#### Running a complete build on a compute cluster

Finally, instead of running the build locally and sequentially, you can run it on a cluster and in parallel. Simply change
the engine:

```
cytograph build --engine condor
```

This will use DAGman to run the build according to the dependency graph. Log files and outputs from the individual steps
are saved in `condor/` in the build folder, which now looks like this:

```
/condor
    _dag.condor
    MySamples_Microglia.condor
    MySamples_Erythrocytes.condor
    MySamples_Endothelial.condor
    MySamples_Fibroblast.condor
    MySamples_Floorplate.condor
    MySamples_NeuralCrest.condor
    MySamples_RadialGlia.condor
    MySamples.condor
    MySamples_Neuronal.condor
    Pool.condor
    ...log files etc...
/data
    MySamples.loom
    MySamples.agg.loom
/exported
    MySamples/
        .
        . Lots of plots
        .
    Pool/
        ...plots...
    ...more folders...
/punchcards
    Root.yaml  # root punchcard, which defines the samples to include in the build
config.yaml    # optional build-specific config
```


