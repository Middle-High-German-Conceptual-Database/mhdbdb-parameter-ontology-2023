#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dhpt import buildOntology as bo
from rdflib.graph import Graph
from dhpt import topQuadrantShacl as shacl
from dhpt import populateTripleStore
import argparse
import subprocess
import logging
import json

if __name__ == "__main__":
    """
        Builds dhpluso ontology, parameter ontology and shape files for dhPlus ontology from source

        Usage:        
        
        $ python build.py --h 
            for parameter list
    """
    

    # Logging
    log = "log/scripts.log"
    logging.basicConfig(filename=log, level=logging.DEBUG,
                        format="%(asctime)s - %(levelname)s - %(message)s")
    
    # Argument parser
    parser = argparse.ArgumentParser(
        description="Build ontology from source"
    )
    parser.add_argument(
        "--nameSpacesJSON",
        type=str,
        default= "../../dhplus_ontology/src/constants/namespaces.json",
        help="Path to namespace json")
    parser.add_argument(
        "--configJSON",
        type=str,
        default= "../../dhplus_ontology/config.json",
        help="Path to config json") 
    parser.add_argument(
        "--sparqlBlocksGlob",
        type=str,        
        default="../src/sparqlBlocks/*.sparql",
        help="sparqlBlocksGlob")
    parser.add_argument(
        "--populateTripleStore",
        type=bool,
        default=False,
        help="If set, dhplus ontology repository will be populated")
    parser.add_argument(
        "--namedGraphTripleStore",
        type=str,
        default='https://dh.plus.sbg.ac.at/graphs/parameterOntology',
        help="The named graph for the vocabularies at the triple store")    
    parser.add_argument(    
        "--noValidation", 
        type=bool,
        default= False,
        help="If set, validation is skipped. Otherwise validation will be generated in /log/validation.ttl.")
    parser.add_argument(
        "--noDocumentation",
        type=bool,
        default= False,
        help="If set, documentation is skipped. Otherwise documentation will be generated in ../doc/ontology with WiDoCo.")
    args = parser.parse_args()
    
    with open(args.configJSON) as json_file:
        config = json.load(json_file)
    with open(args.nameSpacesJSON) as json_file:
        namespaces = json.load(json_file)

    # init ontologyBuilder
    builder = bo.ontologyBuilder(
        nameSpaces=namespaces,
        config=config,
        sparqlBlocksGlob=args.sparqlBlocksGlob
    )

    # build parameter ontology
    logging.info("build parameter ontology")
    dataGraphParameter = builder.buildOntology(
        includePattern="../src/**/*.ttl",
        excludePattern="",
        gitRepoRoot="../",
        filterByClasses=["owl:Ontology", "owl:Class", "owl:DatatypeProperty",
                         "owl:ObjectProperty", "owl:AnnotationProperty"]
    )
    dataGraphParameter.serialize(
        format="turtle", destination="parameterOntology.ttl")

    if args.noValidation is False:
        # Validate dhPlus Parameter Ontology
        logging.info("Validate dhPlus Parameter Ontology")
        validationGraph = builder.buildOntology(
            includePattern="../src/ontologyValidation/**/*.ttl",
            excludePattern="")

        report = shacl.topQuadrantShaclGraph(mode="validate", dataGraph=dataGraphParameter,
                                             shapesGraph=validationGraph, namespaces=namespaces)
        report.serialize(
            destination="log/parameterValidation.ttl", format="turtle")

    if args.noDocumentation is False:
        # Generate documentation of dhPlus Parameter Ontology
        logging.info("Generate documentation of dhPlus Parameter Ontology")
        subprocess.call([
            "java",
            "-jar",
            config["Environment"]["widoco"],
            "-ontFile", "../build/parameterOntology.ttl",
            "-outFolder", "../doc",
            "-rewriteAll",
            "-uniteSections",
            "-lang", "en-de",
            "-excludeIntroduction",
            "-doNotDisplaySerializations",
            "-getOntologyMetadata",
            "-licensius",
        ])

    if args.populateTripleStore is not False:
        # reset and populate triple store        
        repositoryId = config["LocalTripleStoreRepositories"]["dhPLUSOntology"]
        populator = populateTripleStore.populateTripleStore(
            configJson=args.configJSON)
        populator.reset(repositoryId=repositoryId)
        fileList = [            
            "parameterOntology.ttl"
        ]
        populator.populate(fileList=fileList, repositoryId=repositoryId, uri=args.namedGraphTripleStore)
