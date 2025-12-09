import pandas as pd
from lxml import etree
from collections import defaultdict
import re

class XMLConverter:
    """
    Parses a source XML and flattens it into a pandas DataFrame.
    Handles nested elements and multi-valued nodes for complex flattening.
    """

    def _clean_tag(self, tag):
        """Remove namespace prefixes from XML tags."""
        return re.sub(r'\{.*?\}', '', tag)

    def _flatten_element(self, elem, parent_path='', sep='_'):
        """
        Recursively flattens a single XML element and its children into a dictionary.
        Handles lists for multi-valued child elements.
        """
        data = {}
        for child in elem:
            path = f"{parent_path}{sep}{self._clean_tag(child.tag)}" if parent_path else self._clean_tag(child.tag)
            if len(child) > 0:
                # Node has children, recurse
                nested_data = self._flatten_element(child, path, sep)
                # Merge nested data; handle lists by extending them
                for key, value in nested_data.items():
                    if key in data and isinstance(data[key], list):
                        if isinstance(value, list):
                            data[key].extend(value)
                        else:
                            data[key].append(value)
                    elif key in data:
                         data[key] = [data[key], value]
                    else:
                        data[key] = value
            else:
                # Leaf node
                value = child.text.strip() if child.text else ''
                if path in data:
                    if isinstance(data[path], list):
                        data[path].append(value)
                    else:
                        # Convert to list on second occurrence
                        data[path] = [data[path], value]
                else:
                    data[path] = value
        return data

    def convert_to_dataframe(self, xml_path: str, record_tag: str) -> pd.DataFrame:
        """
        Converts an XML file to a pandas DataFrame by flattening records.
        A 'record' is a high-level repeating element in the XML (e.g., a 'Product').

        Args:
            xml_path (str): The path to the XML file.
            record_tag (str): The tag of the repeating element that constitutes a record.

        Returns:
            pd.DataFrame: A flattened DataFrame.
        """
        print(f"Starting XML to DataFrame conversion for {xml_path}...")
        
        # Use iterparse for memory efficiency
        context = etree.iterparse(xml_path, events=('end',), tag=f'*{{{record_tag}}}', recover=True)
        
        records = []
        for _, elem in context:
            flat_record = self._flatten_element(elem)
            
            # Identify list-valued keys to expand into multiple rows
            list_keys = {k for k, v in flat_record.items() if isinstance(v, list)}
            if not list_keys:
                records.append(flat_record)
                elem.clear()
                continue
            
            # Get max length of lists to determine number of new rows
            max_len = max(len(flat_record[k]) for k in list_keys)
            
            # Expand the record into multiple rows
            for i in range(max_len):
                new_record = {}
                for key, value in flat_record.items():
                    if key in list_keys:
                        # Try to get the i-th item, otherwise use None (or last item)
                        try:
                            new_record[key] = value[i]
                        except IndexError:
                            new_record[key] = None
                    else:
                        # Duplicate parent data
                        new_record[key] = value
                records.append(new_record)

            # Free memory
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]

        if not records:
            print("Warning: No records found for the specified record_tag. Returning empty DataFrame.")
            return pd.DataFrame()

        df = pd.DataFrame(records)
        print(f"Successfully converted XML to DataFrame with shape {df.shape}.")
        return df

    def convert_to_csv(self, xml_path: str, csv_path: str, record_tag: str):
        """
        High-level method to convert an XML file directly to a CSV file.
        """
        print(f"Converting {xml_path} to {csv_path}...")
        try:
            df = self.convert_to_dataframe(xml_path, record_tag)
            df.to_csv(csv_path, index=False)
            print(f"Successfully created CSV at {csv_path}.")
        except Exception as e:
            print(f"Error during XML to CSV conversion: {e}")
            raise